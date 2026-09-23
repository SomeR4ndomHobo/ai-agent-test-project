export async function requestJson<T>(path:string, token:string, options:RequestInit={}, signal?:AbortSignal, fetcher:typeof fetch=fetch):Promise<T> {
  const cleanToken=token.trim();
  if(!cleanToken) throw new Error('Enter your backend access token.');
  if(/[^\x20-\x7e]/.test(cleanToken)) throw new Error('The access token contains a line break or unsupported character. Copy only its value from Render Environment.');
  let response:Response;
  try {
    response=await fetcher(path,{...options,signal,headers:{...options.headers,'Content-Type':'application/json',Authorization:`Bearer ${cleanToken}`}});
  } catch(error) {
    if(signal?.aborted) throw error;
    throw new Error('The browser could not connect to the research service. Check your connection and the browser Console for a blocked request.');
  }
  const text=await response.text();
  if(!text.trim()) throw new Error(`The research service returned an empty response (HTTP ${response.status}). Check Render logs and retry.`);
  let data:unknown;
  try {data=JSON.parse(text);} catch {throw new Error(`The research service returned a non-JSON response (HTTP ${response.status}). Check Render logs and the deployed API routes.`);}
  if(!response.ok) {
    const details=data as {detail?:unknown;error?:unknown}|null;
    throw new Error(typeof details?.detail==='string'?details.detail:typeof details?.error==='string'?details.error:`The request failed (HTTP ${response.status}).`);
  }
  return data as T;
}
