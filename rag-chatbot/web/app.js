document.getElementById('ask').onclick = async () => {
  const q = document.getElementById('q').value;
  const out = document.getElementById('out');
  out.textContent = '';
  const apiKey = (window.localStorage.getItem('apiKey') || 'changeme');
  const resp = await fetch('/query', {
    method: 'POST',
    headers: {'content-type':'application/json','x-api-key': apiKey},
    body: JSON.stringify({q})
  });
  const data = await resp.json();
  out.textContent = JSON.stringify(data, null, 2);
};

