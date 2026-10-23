(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('storyboard-data').textContent);
  const get = id => document.getElementById(id);
  const scenes = data.scenes;
  let currentTime = 0, playing = false, previousTime = null, active = -1, animationFrame = null;
  const buttons = [], cards = [];
  const clock = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  get('seek').max = data.duration;
  get('audience').textContent = `读者：${data.audience}。构建版本：${data.version}。`;
  document.querySelector('.outline h2').textContent = `${scenes.length}个镜头一览`;
  scenes.forEach((scene, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = String(index + 1).padStart(2, '0');
    button.setAttribute('aria-label', `镜头${index + 1}：${scene.heading}`);
    button.addEventListener('click', () => select(index));
    get('shot-buttons').append(button); buttons.push(button);
    const card = document.createElement('button'); card.type = 'button'; card.className = 'card';
    card.setAttribute('aria-label', `查看镜头${index + 1}：${scene.heading}`);
    const image = document.createElement('img');
    image.src = `../outputs/scenes/${scene.id}-mobile.png`; image.alt = scene.artwork.alt; image.loading = 'lazy';
    const range = document.createElement('span'); range.textContent = `${scene.start}—${scene.end}秒`;
    const heading = document.createElement('strong'); heading.textContent = scene.heading;
    card.append(image, range, heading); card.addEventListener('click', () => select(index));
    get('cards').append(card); cards.push(card);
  });
  data.references.forEach(reference => {
    const li = document.createElement('li'), link = document.createElement('a');
    link.textContent = `${reference.title} · ${reference.publisher}`; link.href = reference.url;
    li.append(link); get('references').append(li);
  });
  function render() {
    const index = Math.max(0, scenes.findIndex((s, i) => currentTime >= s.start && (currentTime < s.end || i === scenes.length - 1)));
    const scene = scenes[index];
    if (index !== active) {
      active = index;
      get('frame').src = `../outputs/${scene.frame_path}`; get('frame').alt = scene.artwork.alt;
      get('shot-title').textContent = scene.heading;
      get('shot-count').textContent = `镜头 ${String(index + 1).padStart(2, '0')} / ${String(scenes.length).padStart(2, '0')}`;
      get('shot-range').textContent = `${scene.start}—${scene.end}秒`;
      get('narration').textContent = scene.narration;
      get('visual').textContent = scene.visual; get('motion').textContent = scene.motion;
      get('on-screen').textContent = scene.on_screen_text.join(' / ');
      [...buttons, ...cards].forEach((button, i) => button.setAttribute('aria-pressed', String(i % scenes.length === index)));
    }
    const cue = scene.cues.find(c => currentTime >= c.start && currentTime < c.end) || scene.cues[scene.cues.length - 1];
    get('cue').textContent = cue.text;
    get('clock').textContent = `${clock(currentTime)} / ${clock(data.duration)}`;
    get('seek').value = currentTime;
    get('play').textContent = playing ? '暂停预演' : currentTime >= data.duration ? '重新播放' : '播放预演';
  }
  function pause() {
    playing = false; previousTime = null;
    if (animationFrame !== null) cancelAnimationFrame(animationFrame);
    animationFrame = null; render();
  }
  function select(index) { pause(); currentTime = scenes[index].start; render(); }
  function tick(now) {
    animationFrame = null;
    if (!playing) return;
    if (previousTime !== null) currentTime = Math.min(data.duration, currentTime + (now - previousTime) / 1000);
    previousTime = now;
    if (currentTime >= data.duration) { pause(); return; }
    render(); animationFrame = requestAnimationFrame(tick);
  }
  get('play').addEventListener('click', () => {
    if (playing) { pause(); return; }
    if (currentTime >= data.duration) currentTime = 0;
    playing = true; previousTime = null; render(); animationFrame = requestAnimationFrame(tick);
  });
  get('seek').addEventListener('input', event => { const value = Number(event.target.value); pause(); currentTime = value; render(); });
  get('previous').addEventListener('click', () => select(Math.max(0, active - 1)));
  get('next').addEventListener('click', () => select(Math.min(scenes.length - 1, active + 1)));
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  render();
})();
