"""
Knowledge Graph API - Interactive visualization of document relationships.
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.api.deps import require_api_key
from app.services.knowledge_graph import get_knowledge_graph_service

router = APIRouter(prefix="/knowledge", tags=["knowledge-graph"])


@router.get("/graph")
async def get_knowledge_graph(
    api_key: str = Depends(require_api_key)
):
    """Get the interactive knowledge graph visualization data."""
    graph_service = get_knowledge_graph_service()
    
    # Try to get cached graph first
    cached_graph = await graph_service.get_cached_knowledge_graph()
    
    if cached_graph:
        # Convert to visualization format
        visualization_data = {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "group": node.type,
                    "size": node.size,
                    "color": node.color,
                    "title": f"{node.label} ({node.type})",
                    "properties": node.properties
                }
                for node in cached_graph.nodes
            ],
            "edges": [
                {
                    "from": edge.source,
                    "to": edge.target,
                    "label": edge.relationship,
                    "width": max(1, int(edge.strength * 5)),
                    "color": {"opacity": edge.strength},
                    "title": f"{edge.relationship} (strength: {edge.strength:.2f})",
                    "properties": edge.properties
                }
                for edge in cached_graph.edges
            ],
            "clusters": cached_graph.clusters,
            "metadata": cached_graph.metadata,
            "status": "cached"
        }
        
        return visualization_data
    
    # No cached graph available
    return {
        "nodes": [],
        "edges": [],
        "clusters": {},
        "metadata": {
            "total_nodes": 0,
            "total_edges": 0,
            "message": "No knowledge graph available. Upload documents to generate graph."
        },
        "status": "empty"
    }


@router.post("/generate")
async def generate_knowledge_graph(
    api_key: str = Depends(require_api_key)
):
    """Generate a new knowledge graph from all available documents."""
    graph_service = get_knowledge_graph_service()
    
    start_time = time.time()
    
    try:
        # Mock document data - in real implementation, get from database/retriever
        mock_documents = [
            {
                "doc_id": "ai_research",
                "filename": "ai_research.md",
                "content": """
                Artificial Intelligence Research Paper Summary
                
                This research paper explores the applications and implications of artificial intelligence 
                in modern computing systems. The study examines machine learning algorithms, neural networks, 
                and their practical implementations across various industries.
                
                Key Findings:
                - AI systems demonstrate 85% accuracy in pattern recognition tasks
                - Machine learning models reduce processing time by 60% compared to traditional methods
                - Deep learning architectures show superior performance in image classification with 94% accuracy
                - Natural language processing models achieve 78% accuracy in sentiment analysis
                
                The methodology employed a mixed-methods approach with quantitative analysis, qualitative 
                assessment, and experimental design. Data collection spanned multiple sources from 2019-2023.
                
                Applications include healthcare with improved medical diagnosis accuracy by 45%, finance 
                with enhanced fraud detection by 67%, and technology with computer vision achieving 96% 
                object recognition.
                
                Conclusions indicate that artificial intelligence represents a paradigm shift in 
                computational approaches with significant improvements in pattern recognition and 
                predictive modeling.
                """,
                "document_type": "research_paper"
            }
        ]
        
        # Generate the knowledge graph
        knowledge_graph = await graph_service.build_knowledge_graph(mock_documents)
        
        # Get statistics
        statistics = graph_service.get_graph_statistics(knowledge_graph)
        
        generation_time = (time.time() - start_time) * 1000
        
        return {
            "status": "generated",
            "generation_time_ms": round(generation_time, 1),
            "graph_statistics": statistics,
            "preview": {
                "total_nodes": len(knowledge_graph.nodes),
                "total_edges": len(knowledge_graph.edges),
                "clusters": list(knowledge_graph.clusters.keys())
            },
            "message": "Knowledge graph generated successfully. Use /knowledge/graph to view visualization data."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "generation_time_ms": round((time.time() - start_time) * 1000, 1)
        }


@router.get("/stats")
async def get_graph_statistics(
    api_key: str = Depends(require_api_key)
):
    """Get comprehensive statistics about the knowledge graph."""
    graph_service = get_knowledge_graph_service()
    
    cached_graph = await graph_service.get_cached_knowledge_graph()
    
    if cached_graph:
        statistics = graph_service.get_graph_statistics(cached_graph)
        
        # Add additional insights
        statistics["insights"] = {
            "most_important_concepts": [
                node.label for node in sorted(cached_graph.nodes, key=lambda n: n.size, reverse=True)[:5]
                if node.type != "document"
            ],
            "document_coverage": {
                "total_documents": len([n for n in cached_graph.nodes if n.type == "document"]),
                "concepts_per_document": round(
                    len([n for n in cached_graph.nodes if n.type != "document"]) / 
                    max(1, len([n for n in cached_graph.nodes if n.type == "document"])), 1
                )
            },
            "relationship_strength": {
                "strong_connections": len([e for e in cached_graph.edges if e.strength > 0.7]),
                "medium_connections": len([e for e in cached_graph.edges if 0.3 < e.strength <= 0.7]),
                "weak_connections": len([e for e in cached_graph.edges if e.strength <= 0.3])
            }
        }
        
        return statistics
    
    return {
        "error": "No knowledge graph available",
        "message": "Generate a knowledge graph first using /knowledge/generate"
    }


@router.get("/search/{query}")
async def search_graph(
    query: str,
    api_key: str = Depends(require_api_key)
):
    """Search for nodes and relationships in the knowledge graph."""
    graph_service = get_knowledge_graph_service()
    
    cached_graph = await graph_service.get_cached_knowledge_graph()
    
    if not cached_graph:
        return {
            "results": [],
            "message": "No knowledge graph available for search"
        }
    
    query_lower = query.lower()
    matching_nodes = []
    
    # Search nodes by label and properties
    for node in cached_graph.nodes:
        if query_lower in node.label.lower():
            # Calculate relevance score
            relevance = 1.0 if query_lower == node.label.lower() else 0.7
            
            matching_nodes.append({
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "relevance": relevance,
                "size": node.size,
                "color": node.color,
                "properties": node.properties
            })
    
    # Sort by relevance and size
    matching_nodes.sort(key=lambda x: (x["relevance"], x["size"]), reverse=True)
    
    # Find related edges
    node_ids = {node["id"] for node in matching_nodes}
    related_edges = []
    
    for edge in cached_graph.edges:
        if edge.source in node_ids or edge.target in node_ids:
            related_edges.append({
                "source": edge.source,
                "target": edge.target,
                "relationship": edge.relationship,
                "strength": edge.strength
            })
    
    return {
        "query": query,
        "results": {
            "nodes": matching_nodes[:10],  # Top 10 results
            "related_edges": related_edges,
            "total_matches": len(matching_nodes)
        },
        "suggestions": [
            node.label for node in cached_graph.nodes 
            if query_lower in node.label.lower() and node.label.lower() != query_lower
        ][:5]
    }


@router.get("/clusters")
async def get_graph_clusters(
    api_key: str = Depends(require_api_key)
):
    """Get detailed information about graph clusters."""
    graph_service = get_knowledge_graph_service()
    
    cached_graph = await graph_service.get_cached_knowledge_graph()
    
    if not cached_graph:
        return {"clusters": {}, "message": "No knowledge graph available"}
    
    detailed_clusters = {}
    
    for cluster_name, node_ids in cached_graph.clusters.items():
        cluster_nodes = []
        for node_id in node_ids:
            node = next((n for n in cached_graph.nodes if n.id == node_id), None)
            if node:
                cluster_nodes.append({
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    "size": node.size
                })
        
        # Calculate cluster metrics
        total_size = sum(node["size"] for node in cluster_nodes)
        avg_size = total_size / len(cluster_nodes) if cluster_nodes else 0
        
        detailed_clusters[cluster_name] = {
            "nodes": cluster_nodes,
            "node_count": len(cluster_nodes),
            "total_importance": total_size,
            "average_importance": round(avg_size, 1),
            "dominant_types": list(set(node["type"] for node in cluster_nodes))
        }
    
    return {
        "clusters": detailed_clusters,
        "cluster_count": len(detailed_clusters),
        "total_clustered_nodes": sum(len(nodes) for nodes in cached_graph.clusters.values())
    }