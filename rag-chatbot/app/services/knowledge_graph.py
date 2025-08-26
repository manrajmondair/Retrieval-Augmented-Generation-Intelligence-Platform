"""
Knowledge Graph Service - Creates interactive visualizations of document relationships.
"""
import asyncio
import json
import time
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, Counter
import hashlib
import re
from dataclasses import dataclass

from app.services.redis_pool import get_redis_pool
from app.services.fast_llm import get_fast_llm_service


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    label: str
    type: str  # "document", "concept", "topic", "entity"
    properties: Dict[str, Any]
    size: int  # Visual size based on importance
    color: str  # Color based on type


@dataclass
class GraphEdge:
    """Represents a connection in the knowledge graph."""
    source: str
    target: str
    relationship: str  # "mentions", "similar_to", "contains", "references"
    strength: float  # 0-1, connection strength
    properties: Dict[str, Any]


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    clusters: Dict[str, List[str]]  # Topic clusters
    metadata: Dict[str, Any]


class KnowledgeGraphService:
    """Service for building and managing knowledge graphs from documents."""
    
    def __init__(self):
        self.redis_pool = get_redis_pool()
        self.llm_service = get_fast_llm_service()
        
        # Colors for different node types
        self.node_colors = {
            "document": "#4A90E2",    # Blue
            "concept": "#F5A623",     # Orange  
            "topic": "#7ED321",       # Green
            "entity": "#D0021B",      # Red
            "keyword": "#9013FE"      # Purple
        }
        
        # Common important concepts to look for
        self.important_concepts = {
            "technology", "methodology", "analysis", "research", "findings",
            "data", "algorithm", "system", "model", "approach", "framework",
            "results", "conclusion", "recommendation", "strategy", "process"
        }
    
    async def build_knowledge_graph(self, documents_data: List[Dict[str, Any]]) -> KnowledgeGraph:
        """Build a comprehensive knowledge graph from multiple documents."""
        if not documents_data:
            return KnowledgeGraph(nodes=[], edges=[], clusters={}, metadata={})
        
        start_time = time.time()
        
        # Extract entities and concepts from all documents
        all_entities = await self._extract_entities_from_documents(documents_data)
        
        # Build nodes
        nodes = []
        
        # Document nodes
        for doc in documents_data:
            doc_node = GraphNode(
                id=f"doc_{doc['doc_id']}",
                label=doc['filename'],
                type="document",
                properties={
                    "doc_id": doc['doc_id'],
                    "filename": doc['filename'],
                    "content_length": len(doc.get('content', '')),
                    "document_type": doc.get('document_type', 'unknown')
                },
                size=min(50, max(20, len(doc.get('content', '')) // 100)),
                color=self.node_colors["document"]
            )
            nodes.append(doc_node)
        
        # Concept and entity nodes
        entity_importance = self._calculate_entity_importance(all_entities, documents_data)
        
        for entity, importance in entity_importance.items():
            if importance > 0.1:  # Only include important entities
                entity_type = self._classify_entity(entity)
                concept_node = GraphNode(
                    id=f"concept_{hashlib.md5(entity.encode()).hexdigest()[:8]}",
                    label=entity,
                    type=entity_type,
                    properties={
                        "importance": importance,
                        "mentions_count": sum(1 for doc in documents_data if entity.lower() in doc.get('content', '').lower())
                    },
                    size=min(40, max(15, int(importance * 100))),
                    color=self.node_colors.get(entity_type, self.node_colors["concept"])
                )
                nodes.append(concept_node)
        
        # Build edges (relationships)
        edges = await self._build_relationships(nodes, documents_data)
        
        # Create topic clusters
        clusters = self._create_topic_clusters(nodes, edges)
        
        # Build metadata
        metadata = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "document_count": len([n for n in nodes if n.type == "document"]),
            "concept_count": len([n for n in nodes if n.type != "document"]),
            "generation_time_ms": round((time.time() - start_time) * 1000, 1),
            "generated_at": time.time()
        }
        
        graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            clusters=clusters,
            metadata=metadata
        )
        
        # Cache the graph
        await self._cache_knowledge_graph(graph)
        
        return graph
    
    async def _extract_entities_from_documents(self, documents_data: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract key entities and concepts from documents."""
        all_entities = defaultdict(list)
        
        for doc in documents_data:
            content = doc.get('content', '')
            doc_id = doc['doc_id']
            
            # Extract using multiple methods
            entities = set()
            
            # 1. Extract capitalized words (potential proper nouns)
            capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
            entities.update([word for word in capitalized if len(word) > 3])
            
            # 2. Extract important technical terms
            technical_terms = re.findall(r'\b(?:algorithm|methodology|framework|system|model|analysis|approach|technique|method|process|strategy)\w*\b', content.lower())
            entities.update(technical_terms)
            
            # 3. Extract quoted concepts
            quoted_concepts = re.findall(r'"([^"]+)"', content)
            entities.update([concept for concept in quoted_concepts if 3 < len(concept) < 50])
            
            # 4. Extract important concepts from our predefined list
            for concept in self.important_concepts:
                if concept in content.lower():
                    entities.add(concept)
            
            # Clean and filter entities
            filtered_entities = []
            for entity in entities:
                # Filter out common words, very short/long entities
                entity_clean = entity.strip().lower()
                if (len(entity_clean) > 2 and len(entity_clean) < 30 and 
                    entity_clean not in {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from'}):
                    filtered_entities.append(entity_clean)
            
            all_entities[doc_id].extend(filtered_entities)
        
        return all_entities
    
    def _calculate_entity_importance(self, all_entities: Dict[str, List[str]], documents_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate importance scores for entities based on frequency and context."""
        entity_counts = Counter()
        total_documents = len(documents_data)
        
        # Count entity occurrences across documents
        for doc_id, entities in all_entities.items():
            entity_counts.update(entities)
        
        # Calculate importance scores
        importance_scores = {}
        for entity, count in entity_counts.items():
            # Base score from frequency
            frequency_score = min(count / total_documents, 1.0)
            
            # Boost for important concept categories
            category_boost = 1.5 if entity in self.important_concepts else 1.0
            
            # Boost for technical terms
            technical_boost = 1.3 if any(tech in entity for tech in ['algorithm', 'system', 'method', 'analysis']) else 1.0
            
            # Final importance score
            importance = (frequency_score * category_boost * technical_boost) / 2
            importance_scores[entity] = min(importance, 1.0)
        
        return importance_scores
    
    def _classify_entity(self, entity: str) -> str:
        """Classify entity into node types."""
        entity_lower = entity.lower()
        
        if any(tech in entity_lower for tech in ['algorithm', 'system', 'method', 'technique', 'approach']):
            return "concept"
        elif any(topic in entity_lower for topic in ['data', 'analysis', 'research', 'study']):
            return "topic"
        elif entity_lower in self.important_concepts:
            return "concept"
        elif entity[0].isupper():  # Proper noun
            return "entity"
        else:
            return "keyword"
    
    async def _build_relationships(self, nodes: List[GraphNode], documents_data: List[Dict[str, Any]]) -> List[GraphEdge]:
        """Build edges representing relationships between nodes."""
        edges = []
        
        # Create document-concept relationships
        for doc in documents_data:
            doc_node_id = f"doc_{doc['doc_id']}"
            content = doc.get('content', '').lower()
            
            for node in nodes:
                if node.type != "document":
                    # Check if concept appears in document
                    if node.label.lower() in content:
                        # Calculate relationship strength based on frequency
                        mentions = content.count(node.label.lower())
                        strength = min(mentions / 10, 1.0)  # Normalize to 0-1
                        
                        edge = GraphEdge(
                            source=doc_node_id,
                            target=node.id,
                            relationship="mentions",
                            strength=strength,
                            properties={"mentions_count": mentions}
                        )
                        edges.append(edge)
        
        # Create concept-concept relationships (co-occurrence)
        concept_nodes = [n for n in nodes if n.type != "document"]
        for i, concept1 in enumerate(concept_nodes):
            for concept2 in concept_nodes[i+1:]:
                # Calculate co-occurrence across documents
                co_occurrence_count = 0
                total_docs_with_both = 0
                
                for doc in documents_data:
                    content = doc.get('content', '').lower()
                    has_concept1 = concept1.label.lower() in content
                    has_concept2 = concept2.label.lower() in content
                    
                    if has_concept1 and has_concept2:
                        total_docs_with_both += 1
                
                if total_docs_with_both > 0:
                    strength = total_docs_with_both / len(documents_data)
                    
                    if strength > 0.2:  # Only create edge if strong enough relationship
                        edge = GraphEdge(
                            source=concept1.id,
                            target=concept2.id,
                            relationship="related_to",
                            strength=strength,
                            properties={"co_occurrence_docs": total_docs_with_both}
                        )
                        edges.append(edge)
        
        return edges
    
    def _create_topic_clusters(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict[str, List[str]]:
        """Create topic-based clusters of related nodes."""
        clusters = defaultdict(list)
        
        # Simple clustering based on node types and connections
        document_nodes = [n for n in nodes if n.type == "document"]
        concept_nodes = [n for n in nodes if n.type == "concept"]
        topic_nodes = [n for n in nodes if n.type == "topic"]
        
        clusters["Documents"] = [n.id for n in document_nodes]
        clusters["Core Concepts"] = [n.id for n in concept_nodes]
        clusters["Topics"] = [n.id for n in topic_nodes]
        
        # Create technology cluster
        tech_nodes = [n for n in nodes if any(tech in n.label.lower() for tech in ['algorithm', 'system', 'method', 'technology'])]
        if tech_nodes:
            clusters["Technology"] = [n.id for n in tech_nodes]
        
        # Create research cluster  
        research_nodes = [n for n in nodes if any(research in n.label.lower() for research in ['research', 'analysis', 'study', 'findings'])]
        if research_nodes:
            clusters["Research"] = [n.id for n in research_nodes]
        
        return dict(clusters)
    
    async def _cache_knowledge_graph(self, graph: KnowledgeGraph):
        """Cache the knowledge graph for quick access."""
        try:
            cache_key = "knowledge_graph:main"
            graph_data = {
                "nodes": [
                    {
                        "id": node.id,
                        "label": node.label,
                        "type": node.type,
                        "properties": node.properties,
                        "size": node.size,
                        "color": node.color
                    }
                    for node in graph.nodes
                ],
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "relationship": edge.relationship,
                        "strength": edge.strength,
                        "properties": edge.properties
                    }
                    for edge in graph.edges
                ],
                "clusters": graph.clusters,
                "metadata": graph.metadata
            }
            
            await self.redis_pool.set_with_optimization(
                cache_key,
                json.dumps(graph_data).encode('utf-8'),
                1800,  # 30 minute TTL
                "cache"
            )
            
        except Exception:
            pass  # Continue without caching
    
    async def get_cached_knowledge_graph(self) -> Optional[KnowledgeGraph]:
        """Get cached knowledge graph."""
        try:
            cache_key = "knowledge_graph:main"
            cached_data = await self.redis_pool.get_with_fallback(cache_key, "cache")
            
            if cached_data:
                graph_data = json.loads(cached_data.decode('utf-8'))
                
                # Reconstruct nodes
                nodes = []
                for node_data in graph_data["nodes"]:
                    node = GraphNode(
                        id=node_data["id"],
                        label=node_data["label"],
                        type=node_data["type"],
                        properties=node_data["properties"],
                        size=node_data["size"],
                        color=node_data["color"]
                    )
                    nodes.append(node)
                
                # Reconstruct edges
                edges = []
                for edge_data in graph_data["edges"]:
                    edge = GraphEdge(
                        source=edge_data["source"],
                        target=edge_data["target"],
                        relationship=edge_data["relationship"],
                        strength=edge_data["strength"],
                        properties=edge_data["properties"]
                    )
                    edges.append(edge)
                
                return KnowledgeGraph(
                    nodes=nodes,
                    edges=edges,
                    clusters=graph_data["clusters"],
                    metadata=graph_data["metadata"]
                )
            
        except Exception:
            pass
        
        return None
    
    def get_graph_statistics(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge graph."""
        node_types = Counter([node.type for node in graph.nodes])
        relationship_types = Counter([edge.relationship for edge in graph.edges])
        
        # Calculate network metrics
        total_connections = len(graph.edges)
        avg_connections_per_node = total_connections / len(graph.nodes) if graph.nodes else 0
        
        # Find most connected nodes
        node_connections = Counter()
        for edge in graph.edges:
            node_connections[edge.source] += 1
            node_connections[edge.target] += 1
        
        most_connected = node_connections.most_common(5)
        
        return {
            "network_metrics": {
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "average_connections": round(avg_connections_per_node, 2),
                "density": round(total_connections / (len(graph.nodes) * (len(graph.nodes) - 1)) * 2, 3) if len(graph.nodes) > 1 else 0
            },
            "node_distribution": dict(node_types),
            "relationship_distribution": dict(relationship_types),
            "most_connected_nodes": [
                {
                    "node_id": node_id,
                    "connections": count,
                    "label": next((n.label for n in graph.nodes if n.id == node_id), "Unknown")
                }
                for node_id, count in most_connected
            ],
            "cluster_sizes": {cluster: len(nodes) for cluster, nodes in graph.clusters.items()}
        }


# Global instance
_knowledge_graph_service = None

def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get or create the knowledge graph service singleton."""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service