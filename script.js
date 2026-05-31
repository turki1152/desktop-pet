// Live clock in hero
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const el = document.getElementById('clock');
  const el2 = document.getElementById('clockDate');
  if (el) el.textContent = `${h}:${m}`;
  if (el2) el2.textContent = `${days[now.getDay()]} ${now.getDate()}`;
}
updateClock();
setInterval(updateClock, 10000);

// Mobile menu
const burger = document.getElementById('burger');
const mobileMenu = document.getElementById('mobileMenu');
if (burger && mobileMenu) {
  burger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
  });
}
function closeMenu() {
  if (mobileMenu) mobileMenu.classList.remove('open');
}

// Scroll animations
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  },
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
);

document.querySelectorAll('.feat-card, .char-card, .stat-item, .step, .faq-item').forEach((el, i) => {
  el.classList.add('fade-up');
  el.style.transitionDelay = `${(i % 4) * 80}ms`;
  observer.observe(el);
});

// Sticky nav shadow on scroll
window.addEventListener('scroll', () => {
  const nav = document.getElementById('nav');
  if (nav) {
    nav.style.background = window.scrollY > 20
      ? 'rgba(8, 9, 13, 0.95)'
      : 'rgba(8, 9, 13, 0.7)';
  }
}, { passive: true });

// Rotate pet bubble messages
const bubbleMessages = [
  'Hello! ☀️', "Pat me! 🐾", "Good vibes ✨", "I'm here! 😊",
  "So bored... 😴", "Weather's nice!", "Meow 🐱"
];
let bubbleIdx = 0;
const bubbleEl = document.querySelector('.pet-bubble');
if (bubbleEl) {
  setInterval(() => {
    bubbleIdx = (bubbleIdx + 1) % bubbleMessages.length;
    bubbleEl.style.opacity = '0';
    setTimeout(() => {
      bubbleEl.textContent = bubbleMessages[bubbleIdx];
      bubbleEl.style.opacity = '1';
    }, 300);
  }, 3000);
}
