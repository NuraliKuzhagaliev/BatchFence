"""Authenticated local reference contract. This is NOT an enterprise inventory adapter."""
import json
import os
import secrets
import sqlite3
import uuid
import asyncio
from contextlib import closing
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from .domain import digest
from .fixtures import now,ROOT

app=FastAPI(title='BatchFence local sandbox reference connector')
class Action(BaseModel):
    model_config=ConfigDict(extra='forbid')
    hold_id:str=Field(max_length=100)
    hold_version:int=Field(ge=1)
    pool_id:str=Field(max_length=160)
    units:int=Field(ge=1,le=9_000_000_000)
    disposition:Literal['remove_incident_restriction']
class Operation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation_id:str=Field(pattern='^[a-f0-9]{64}$')
    scope_hash:str=Field(pattern='^[a-f0-9]{64}$')
    actions:list[Action]=Field(min_length=1,max_length=80)


@app.middleware('http')
async def protect(request:Request,call_next):
    from fastapi.responses import JSONResponse
    token=os.getenv('REFERENCE_CONNECTOR_TOKEN','')
    if len(token)<32 or not secrets.compare_digest(request.headers.get('authorization',''),'Bearer '+token):return JSONResponse({'error':'Unauthorized'},401)
    try:
        if int(request.headers.get('content-length','0'))>64000:return JSONResponse({'error':'Request limit'},413)
        async def bounded():
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>64000:raise OverflowError()
                chunks.append(chunk)
            request._body=b''.join(chunks)
        await asyncio.wait_for(bounded(),5)
    except OverflowError:return JSONResponse({'error':'Request limit'},413)
    except (ValueError,asyncio.TimeoutError):return JSONResponse({'error':'Invalid body'},400)
    return await call_next(request)


@app.post('/inventory/restrictions')
def acknowledge(data:Operation):
    path=Path(os.getenv('REFERENCE_DATABASE_PATH') or ROOT/'work/reference-inventory.sqlite3')
    payload=data.model_dump();fingerprint=digest(payload)
    with closing(sqlite3.connect(path,timeout=10)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,digest TEXT NOT NULL,receipt TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT digest,receipt FROM operations WHERE id=?',(data.operation_id,)).fetchone()
        if prior:
            if prior[0]!=fingerprint:raise HTTPException(409,'Idempotency conflict')
            return json.loads(prior[1])
        receipt={'acknowledgement_id':'REF-'+uuid.uuid4().hex,'at':now(),'operation_id':data.operation_id,'request_digest':fingerprint,
                 'execution':'LOCAL SANDBOX REFERENCE','removed_restriction_ids':[a.hold_id for a in data.actions],
                 'physical_enterprise_action':False}
        db.execute('INSERT INTO operations VALUES(?,?,?)',(data.operation_id,fingerprint,json.dumps(receipt)))
        return receipt
