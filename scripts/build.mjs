import {build} from 'esbuild';import {mkdir,copyFile,readFile,writeFile,rm} from 'node:fs/promises';
await rm('dist',{recursive:true,force:true});await mkdir('dist/src',{recursive:true});
for(const file of ['style.css','icon.svg','config.js'])await copyFile('client/'+file,'dist/'+file);
await copyFile('client/index.html','dist/index.html');
if(process.env.API_URL){if(!process.env.API_URL.startsWith('https://'))throw new Error('APK API_URL must use HTTPS');await writeFile('dist/config.js','window.ESCAPE_CONFIG = '+JSON.stringify({apiBase:process.env.API_URL})+';');}
await build({entryPoints:['client/src/app.js'],bundle:true,format:'esm',target:'es2020',outfile:'dist/src/app.js',minify:true});
console.log('Built player assets in dist. Set API_URL to your backend before Android sync.');
