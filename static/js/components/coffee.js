/**
 * Feature Bullshit : Bouton Pause Café & Anti-Procrastination.
 * Déclenche une pluie d'émojis, des punchlines aléatoires, un carillon audio
 * et un compteur de tasses bues pour fuir le travail.
 */

const PUNCHLINES = [
  "« Procrastiner, c'est l'art de garder pour demain ce qu'on peut très bien ne pas faire du tout. »",
  "« Faire une To-Do List sans cocher de cases, c'est déjà 80% du travail psychologique accompli. »",
  "« Tâche marquée comme terminée avec succès dans un univers parallèle. Bravo ! »",
  "« Un café virtuel a été injecté dans vos veines. Niveau d'énergie : +42%. »",
  "« Votre volonté de travailler a temporairement quitté la conversation. »",
  "« Félicitations ! Vous venez de cliquer sur ce bouton inutile au lieu d'avancer sur vos priorités. »",
  "« Il n'y a pas de problème qu'une pause café bien méritée ne puisse temporairement ignorer. »",
  "« Bug ou fonctionnalité ? Pourquoi choisir quand on peut avoir les deux. »",
  "« Statut officiel : En train de faire semblant d'être très occupé. »",
  "« C'est prouvé scientifiquement : regarder sa liste de tâches brûle 0.4 calorie par minute. »",
  "« Procrastination niveau Maître Jedi activée. Que la flemme soit avec toi. »",
  "« Ce message s'autodétruira dès que tu auras coché une tâche. Donc probablement jamais. »",
  "« En cas de doute, fais une pause café. En cas de certitude, prends-en deux. »",
  "« Votre niveau de productivité vient d'augmenter de 0.00001%. Chaque micro-victoire compte. »",
  "« Rappel amical : la meilleure façon de commencer une tâche... c'est de ranger son bureau d'abord. »"
];

const EMOJIS = ['☕', '🎉', '🦥', '🚀', '🍩', '🍕', '💻', '🧠', '✨', '💤', '🪄', '⭐'];

function getRank(count) {
  if (count <= 3) return "Débutant de la flemme 🥱";
  if (count <= 10) return "Amateur de pauses café ☕";
  if (count <= 25) return "Expert en procrastination 🦥";
  if (count <= 50) return "Grand Maître du Report au Lendemain 🧘";
  return "Légende Vivante de l'Inaction 👑";
}

function playCoffeeChime() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const notes = [523.25, 659.25, 783.99, 1046.50]; // Do, Mi, Sol, Do (arpège joyeux)
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.09);
      gain.gain.setValueAtTime(0.001, ctx.currentTime + idx * 0.09);
      gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + idx * 0.09 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.09 + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.09);
      osc.stop(ctx.currentTime + idx * 0.09 + 0.4);
    });
  } catch (e) {
    // Audio autoplay restreint ou non supporté
  }
}

function launchEmojiShower() {
  const container = document.createElement('div');
  container.className = 'emoji-shower-container';
  document.body.appendChild(container);

  const count = 35;
  for (let i = 0; i < count; i++) {
    const span = document.createElement('span');
    span.className = 'falling-emoji';
    span.textContent = EMOJIS[Math.floor(Math.random() * EMOJIS.length)];
    span.style.left = `${Math.random() * 96 + 2}vw`;
    span.style.animationDuration = `${1.8 + Math.random() * 1.5}s`;
    span.style.animationDelay = `${Math.random() * 0.6}s`;
    span.style.fontSize = `${1.5 + Math.random() * 1.8}rem`;
    container.appendChild(span);
  }

  setTimeout(() => {
    container.remove();
  }, 4000);
}

export function openCoffeeModal() {
  const modal = document.getElementById('coffee-modal');
  if (!modal) return;

  // Compteur persisté
  let count = parseInt(localStorage.getItem('todolist_coffee_breaks_count') || '0', 10);
  count += 1;
  localStorage.setItem('todolist_coffee_breaks_count', count.toString());

  // Mise à jour de la quote aléatoire
  const quoteEl = document.getElementById('coffee-quote-text');
  if (quoteEl) {
    quoteEl.textContent = PUNCHLINES[Math.floor(Math.random() * PUNCHLINES.length)];
  }

  // Mise à jour du compteur et du rang
  const countEl = document.getElementById('coffee-count-display');
  if (countEl) {
    countEl.textContent = `${count} tasse${count > 1 ? 's' : ''} bue${count > 1 ? 's' : ''}`;
  }

  const rankEl = document.getElementById('coffee-rank-display');
  if (rankEl) {
    rankEl.textContent = getRank(count);
  }

  modal.classList.remove('hidden');
  playCoffeeChime();
  launchEmojiShower();
}

export function initCoffeeFeature() {
  const btn = document.getElementById('coffee-break-btn');
  const modal = document.getElementById('coffee-modal');
  const closeBtn = document.getElementById('coffee-modal-close-btn');
  const anotherBtn = document.getElementById('coffee-another-btn');
  const backToWorkBtn = document.getElementById('coffee-back-to-work-btn');

  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openCoffeeModal();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal?.classList.add('hidden');
    });
  }

  if (anotherBtn) {
    anotherBtn.addEventListener('click', () => {
      openCoffeeModal();
    });
  }

  if (backToWorkBtn) {
    backToWorkBtn.addEventListener('click', () => {
      modal?.classList.add('hidden');
      launchEmojiShower();
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });
  }
}
