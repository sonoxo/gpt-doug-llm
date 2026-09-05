// A blank canvas. An open browser. Endless possibilities.
const button = document.querySelector('#launch');

button.addEventListener('click', () => {
  button.textContent = 'You made it happen ✨';
  console.log('Your first interaction is live!');
});

console.log('Hello, Orbit! Your app is ready.');
