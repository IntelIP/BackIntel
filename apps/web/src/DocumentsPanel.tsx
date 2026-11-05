import {useState} from 'react';

export type SourceDocument = {id:string;title:string;source_url:string|null;bytes:number;payload_sha256:string};
export type DocumentCitation = {document_id:string;passage_id:string;quote:string;field:string;table:string;schema:string;title:string;source_url:string|null};
export type DocumentUpload = {title:string;source_url:string|null;media_type:string;content_base64:string};

export function DocumentCitations({items,onInspect}:{items:DocumentCitation[];onInspect:(id:string)=>void}) {
  if (!items.length) return null;
  return <section aria-label="Supporting document passages"><h3>Supporting document passages</h3>
    <p>These quotations explain source fields. The calculation checks still apply.</p>
    {items.map((item,index)=><article key={item.document_id+item.passage_id+item.field+index}>
      <h4>{item.field} · {item.title}</h4><blockquote>{item.quote}</blockquote>
      {item.source_url&&<p><a href={item.source_url} target="_blank" rel="noreferrer">Source document</a></p>}
      <button onClick={()=>onInspect(item.document_id)}>Inspect retained document for {item.field}</button>
    </article>)}
  </section>;
}

export function DocumentsPanel({documents,canManage,busy,onAttach,onRemove,onInspect,onDownload}: {
  documents:SourceDocument[];canManage:boolean;busy:boolean;
  onAttach:(value:DocumentUpload)=>Promise<void>;onRemove:(id:string)=>void;
  onInspect:(id:string)=>void;onDownload:(id:string)=>void;
}) {
  const [title,setTitle]=useState('');
  const [url,setUrl]=useState('');
  const [file,setFile]=useState<File|null>(null);
  const [mediaType,setMediaType]=useState('text/plain');
  const [reading,setReading]=useState(false);
  const [error,setError]=useState('');
  const disabled=busy||reading;
  async function attach() {
    setError('');
    if (!file||!file.size||file.size>2_000_000) {setError('Choose a nonempty UTF-8 text or HTML file, up to 2 MB.');return;}
    setReading(true);
    try {
      const encoded=await new Promise<string>((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(String(reader.result).split(',')[1]);
        reader.onerror=()=>reject(new Error('The document could not be read.'));
        reader.readAsDataURL(file);
      });
      await onAttach({title,source_url:url||null,media_type:mediaType,content_base64:encoded});
    } catch (value) {setError(value instanceof Error?value.message:'The document could not be attached.');}
    finally {setReading(false);}
  }
  return <section aria-label="Source documents"><h2>Source documents</h2>
    <p>Attach a field guide or business definition. BackIntel retains the original and quotes supporting passages beside the answer.</p>
    <p>Adding or removing a document creates a new goal version. Confirm and check that version before saving its workflow.</p>
    {documents.length===0&&<p>No documents attached.</p>}
    {documents.map(document=><article key={document.id}><h3>{document.title}</h3>
      {document.source_url&&<p><a href={document.source_url} target="_blank" rel="noreferrer">Source reference</a></p>}
      <p>{document.bytes.toLocaleString()} original bytes retained.</p>
      <button disabled={disabled} onClick={()=>onInspect(document.id)}>Inspect {document.title}</button>
      <button disabled={disabled} onClick={()=>onDownload(document.id)}>Download original {document.title}</button>
      {canManage&&<button disabled={disabled} onClick={()=>onRemove(document.id)}>Detach {document.title}</button>}
    </article>)}
    {canManage&&<form onSubmit={event=>{event.preventDefault();void attach();}}>
      <label>Document title<input value={title} onChange={event=>setTitle(event.target.value)} required maxLength={200}/></label>
      <label>Source URL (optional)<input type="url" value={url} onChange={event=>setUrl(event.target.value)} maxLength={2000}/></label>
      <label>Document file<input type="file" accept=".txt,.html,.htm,text/plain,text/html" required onChange={event=>{
        const selected=event.target.files?.[0]||null;setFile(selected);
        if(selected) {setMediaType(selected.type==='text/html'||/\.html?$/i.test(selected.name)?'text/html':'text/plain');if(!title)setTitle(selected.name);}
      }}/></label>
      <label>Document format<select value={mediaType} onChange={event=>setMediaType(event.target.value)}>
        <option value="text/plain">UTF-8 plain text</option><option value="text/html">UTF-8 HTML</option>
      </select></label>
      <p>Up to four documents, 2 MB each. PDF and scanned images are not supported yet.</p>
      <button disabled={disabled||documents.length>=4}>Attach document</button>
    </form>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
