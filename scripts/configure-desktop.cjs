// Bake only the public service origin. Never reads AMD keys or private .env files.
const fs=require('node:fs'),path=require('node:path');
function validateOrigin(value){
 const u=new URL(value);
 if(!(u.protocol==='https:'||(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)))||
   u.username||u.password||u.pathname!=='/'||u.search||u.hash)throw Error('Desktop origin must be HTTPS (or loopback HTTP), with no credentials, path, query or fragment.');
 return u.origin;
}
if(require.main===module){
 const config=path.resolve(__dirname,'../desktop/backend-origin.json');
 const prior=JSON.parse(fs.readFileSync(config,'utf8')).origin;
 const origin=validateOrigin(process.env.BATCHFENCE_BACKEND_ORIGIN||prior);
 fs.writeFileSync(config,JSON.stringify({origin},null,2)+'\n');
 console.log('Desktop public backend origin configuration validated.');
}
module.exports={validateOrigin};
