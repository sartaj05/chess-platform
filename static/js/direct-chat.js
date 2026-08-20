(() => {
  const shell = document.querySelector('[data-chat-thread]');
  const form = document.getElementById('realtimeChatForm');
  const timeline = document.getElementById('chatTimeline');
  if (!shell || !form || !timeline || !window.WebSocket) return;
  const userId = shell.dataset.userId;
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${scheme}://${location.host}/ws/chat/${shell.dataset.chatThread}/`);
  const input = form.querySelector('textarea');
  const escape = (value) => { const node=document.createElement('div'); node.textContent=value; return node.innerHTML; };
  const scroll = () => timeline.scrollTop = timeline.scrollHeight;
  scroll();
  let heartbeat;
  socket.addEventListener('open', () => {
    socket.send(JSON.stringify({type:'chat.read'}));
    heartbeat=window.setInterval(()=>socket.readyState===WebSocket.OPEN&&socket.send(JSON.stringify({type:'presence.ping'})),30000);
  });
  socket.addEventListener('close',()=>window.clearInterval(heartbeat));
  socket.addEventListener('message', (event) => {
    const data=JSON.parse(event.data);
    if(data.type==='chat.message'){
      timeline.querySelector('.chat-empty')?.remove(); const mine=String(data.message.sender_id)===String(userId);
      timeline.insertAdjacentHTML('beforeend',`<article data-message-id="${data.message.id}" class="chat-message ${mine?'sent':'received'}"><div class="message-bubble">${escape(data.message.body)}</div><div class="message-meta"><time>Now</time>${mine?'<small class="delivery-state">Sent</small>':''}</div></article>`); scroll();
      if(!mine) socket.send(JSON.stringify({type:'chat.read'}));
    } else if(data.type==='chat.read' && String(data.user_id)!==String(userId)) document.querySelectorAll('.chat-message.sent .delivery-state').forEach(el=>el.textContent='Read');
    else if(data.type==='presence' && String(data.user_id)!==String(userId)){const el=document.getElementById('chatPresence');if(el)el.textContent=data.online?'Online':'Offline';}
  });
  form.addEventListener('submit',(event)=>{if(socket.readyState!==WebSocket.OPEN)return;event.preventDefault();const body=input.value.trim();if(!body)return;socket.send(JSON.stringify({type:'chat.send',body}));input.value='';});
})();
