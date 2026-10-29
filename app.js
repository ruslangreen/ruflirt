const $=id=>document.getElementById(id);
let recognition=null,active=false,last='',busy=false,startTimer=null,partialTimer=null,session=0,restartTimer=null,restartCount=0,hadSpeech=false,segment='',segmentFinal='',segmentSent=false,requestSeq=0;
const history=[];
const templates=[[/сколько тебе лет|возраст/i,'Мне 42. А ты всегда начинаешь знакомство с допроса? 😄'],[/зачем (ты )?(здесь|сюда)|что (ты )?тут делаешь/i,'Зашёл пообщаться. А ты уже успела найти здесь кого-то интересного?'],[/как дела|как ты/i,'Вполне хорошо. А у тебя сегодня что было самым приятным?'],[/чем занимаешься|кем работаешь/i,'Работаю с технологиями, чтобы они делали скучное за людей. А ты чем увлечена?'],[/откуда ты|где живешь/i,'Из Подмосковья. А ты из какого города?'],[/как тебя зовут|имя/i,'Руслан. А тебя как зовут?'],[/привет|здравствуй/i,'Привет! Как проходит твой вечер?']];
function fallback(t){for(const [re,v] of templates)if(re.test(t))return v;return 'Интересно! А как ты к этому пришла?'}
function status(t){$('status').textContent='● '+t}
async function suggest(t){t=t.trim();if(!t||t===last)return;last=t;$('heard').textContent=t;const endpoint=$('endpoint').value.trim();if(!endpoint){$('suggestion').textContent=fallback(t);history.push({speaker:'other',text:t});return}busy=true;const requestId=++requestSeq;status('Готовлю ответ');const ctrl=new AbortController();const timeout=setTimeout(()=>ctrl.abort(),8000);try{const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json',...($('accessToken').value?{'Authorization':'Bearer '+$('accessToken').value}:{})},body:JSON.stringify({text:t,history:history.slice(-8)}),signal:ctrl.signal});if(!r.ok)throw Error('HTTP '+r.status);const data=await r.json();if(requestId===requestSeq)$('suggestion').textContent=String(data.suggestion||fallback(t)).slice(0,240);history.push({speaker:'other',text:t},{speaker:'assistant',text:data.suggestion||''})}catch(e){if(requestId===requestSeq)$('suggestion').textContent='Нет ответа AI: '+(e.name==='AbortError'?'превышено время ожидания':e.message)}finally{clearTimeout(timeout);busy=false;status(active?'Слушаю':'Готов')}}
function cleanup(){clearTimeout(startTimer);clearTimeout(partialTimer);clearTimeout(restartTimer);startTimer=null;partialTimer=null;restartTimer=null}
function stop(message='Остановлен'){active=false;session++;cleanup();const r=recognition;recognition=null;if(r){r.onend=null;r.onerror=null;r.onresult=null;try{r.abort()}catch{}}status(message);$('start').disabled=false}
function start(){
 if(active)return;
 restartCount=0;active=true;beginListening();
}
function beginListening(){
 if(!active||document.hidden)return;
 cleanup();
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){status('Распознавание недоступно');$('heard').textContent='Safari не предоставляет распознавание речи. Проверь тестовый ввод ниже.';return}
 const current=++session;hadSpeech=false;segment='';segmentFinal='';segmentSent=false;$('start').disabled=true;status('Подключаю микрофон');
 const r=new SR();recognition=r;r.lang='ru-RU';r.continuous=true;r.interimResults=true;
 r.onstart=()=>{if(current!==session)return;clearTimeout(startTimer);status('Слушаю')};
 function flushSegment(){clearTimeout(partialTimer);if(!segmentSent&&segment.trim()){segmentSent=true;suggest(segment.trim())}}
 r.onresult=e=>{
  if(current!==session)return;
  let finals=[],interims=[];
  for(let i=0;i<e.results.length;i++){
   const v=e.results[i][0].transcript.trim();
   if(e.results[i].isFinal)finals.push(v);else interims.push(v);
  }
  const finalText=finals.join(' ').trim();
  const interimText=interims.join(' ').trim();
  const full=(finalText+' '+interimText).trim();
  if(!full)return;
  hadSpeech=true;restartCount=0;
  if(segmentSent&&full!==segment){segmentSent=false;segmentFinal='';last=''}
  segment=full;segmentFinal=finalText;
  $('heard').textContent=full;
  clearTimeout(partialTimer);
  // Short silence ends a thought; don't send every interim fragment.
  partialTimer=setTimeout(()=>{if(current!==session||!active)return;flushSegment();try{r.stop()}catch{}},1200);
 };

 r.onerror=e=>{if(current!==session)return;if(e.error==='no-speech'){status('Жду речь');return}const names={ 'not-allowed':'Нет доступа к микрофону','audio-capture':'Микрофон недоступен','network':'Ошибка сервиса распознавания','language-not-supported':'Русский язык не поддерживается','no-speech':'Речь не обнаружена','aborted':'Остановлено'};stop(names[e.error]||('Ошибка: '+e.error))};
 r.onend=()=>{if(current!==session||!active)return;flushSegment();clearTimeout(startTimer);if(document.hidden){stop('Открой RuFlirt на экране для прослушивания');return}restartCount++;if(restartCount>8&&!hadSpeech){stop('Safari остановил распознавание. Нажми «Слушать» снова');return}status('Переподключаю микрофон');restartTimer=setTimeout(()=>{if(active&&current===session)beginListening()},Math.min(300+restartCount*150,1200))};
 startTimer=setTimeout(()=>{if(current===session&&active)stop('Микрофон не запустился за 8 секунд. Попробуй Safari или перезагрузку страницы')},8000);
 try{r.start()}catch(e){stop('Не удалось запустить распознавание: '+e.message)}
}
$('start').onclick=start;$('stop').onclick=()=>stop();$('test').onclick=()=>suggest($('manual').value);
if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js').catch(()=>{});

document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)stop('В фоне микрофон недоступен — вернись в RuFlirt')});

/* Remember the private proxy settings on this device only. */
try {
 const savedEndpoint=localStorage.getItem('ruflirt_endpoint');
 const savedToken=localStorage.getItem('ruflirt_token');
 if(savedEndpoint)$('endpoint').value=savedEndpoint;
 if(savedToken)$('accessToken').value=savedToken;
 $('endpoint').addEventListener('input',()=>localStorage.setItem('ruflirt_endpoint',$('endpoint').value.trim()));
 $('accessToken').addEventListener('input',()=>localStorage.setItem('ruflirt_token',$('accessToken').value));
} catch(e) { /* Private browsing may block storage. */ }
