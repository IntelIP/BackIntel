import React from 'react';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {DocumentsPanel,DocumentCitations} from '../src/DocumentsPanel';

afterEach(cleanup);
const document={id:'doc',title:'Retail field guide',source_url:'https://example.org/guide',bytes:45,payload_sha256:'hash'};

describe('source documents',()=>{
  it('lets a reader inspect originals without changing the objective',()=>{
    const inspect=vi.fn(),download=vi.fn();
    render(<DocumentsPanel documents={[document]} canManage={false} busy={false} onAttach={vi.fn()} onRemove={vi.fn()} onInspect={inspect} onDownload={download}/>);
    expect(screen.queryByRole('button',{name:'Attach document'})).toBeNull();
    expect(screen.queryByRole('button',{name:'Detach Retail field guide'})).toBeNull();
    fireEvent.click(screen.getByRole('button',{name:'Inspect Retail field guide'}));
    fireEvent.click(screen.getByRole('button',{name:'Download original Retail field guide'}));
    expect(inspect).toHaveBeenCalledWith('doc');expect(download).toHaveBeenCalledWith('doc');
  });
  it('preserves file bytes and explains that attachments require new checks',async()=>{
    const attach=vi.fn().mockResolvedValue(undefined);
    render(<DocumentsPanel documents={[]} canManage busy={false} onAttach={attach} onRemove={vi.fn()} onInspect={vi.fn()} onDownload={vi.fn()}/>);
    expect(screen.getByText(/Adding or removing a document creates a new goal version/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Document file'),{target:{files:[new File(['InvoiceNo: c means cancellation.'],'guide.txt',{type:'text/plain'})]}});
    fireEvent.submit(screen.getByRole('button',{name:'Attach document'}).closest('form')!);
    await waitFor(()=>expect(attach).toHaveBeenCalledWith(expect.objectContaining({title:'guide.txt',media_type:'text/plain',content_base64:btoa('InvoiceNo: c means cancellation.')})));
  });
  it('displays hostile markup as a quotation without executing it',()=>{
    const inspect=vi.fn();
    render(<DocumentCitations items={[{document_id:'doc',passage_id:'p',field:'InvoiceNo',table:'lines',schema:'retail',title:'Guide',source_url:null,quote:'<script>steal()</script> InvoiceNo: c means cancellation.'}]} onInspect={inspect}/>);
    expect(screen.getByText('<script>steal()</script> InvoiceNo: c means cancellation.')).toBeTruthy();
    expect(window.document.querySelector('script')).toBeNull();
    fireEvent.click(screen.getByRole('button',{name:'Inspect retained document for InvoiceNo'}));
    expect(inspect).toHaveBeenCalledWith('doc');
  });
});
