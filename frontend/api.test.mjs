import {test} from 'node:test';
import assert from 'node:assert/strict';
import {requestJson} from './lib/api.ts';
test('trims pasted token whitespace',async()=>{
 const result=await requestJson('/health',' token-value \r\n',{},undefined,async(_,opts)=>{assert.equal(opts.headers.Authorization,'Bearer token-value');return new Response('{"status":"ready"}');});
 assert.equal(result.status,'ready');
});
test('reports embedded line breaks before making a request',async()=>{
 await assert.rejects(requestJson('/health','token\nvalue',{},undefined,async()=>{assert.fail('must not fetch');}),/line break/);
});
test('reports unsupported token characters',async()=>{
 await assert.rejects(requestJson('/health','token–value'),/unsupported character/);
});
test('preserves authentication errors',async()=>{
 await assert.rejects(requestJson('/health','token',{},undefined,async()=>new Response('{"detail":"Invalid backend access token."}',{status:401})),/Invalid backend access token/);
});
test('explains an empty service response',async()=>{
 await assert.rejects(requestJson('/health','token',{},undefined,async()=>new Response('',{status:503})),/empty response.*503/);
});
test('explains network failures',async()=>{
 await assert.rejects(requestJson('/health','token',{},undefined,async()=>{throw new TypeError('Failed to fetch');}),/browser could not connect/);
});
