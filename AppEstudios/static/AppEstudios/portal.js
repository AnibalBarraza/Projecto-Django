/* Native dialog enhancement; the create link also works without JavaScript. */
(() => {
  document.querySelectorAll('[data-open-dialog]').forEach(link => {
    link.addEventListener('click', event => {
      const dialog = document.getElementById(link.dataset.openDialog);
      if (!dialog || typeof dialog.showModal !== 'function') return;
      event.preventDefault();
      dialog.showModal();
    });
  });
  document.querySelectorAll('[data-close-dialog]').forEach(button => {
    button.addEventListener('click', () => button.closest('dialog').close());
  });
})();
