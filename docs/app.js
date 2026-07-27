const backupTab = document.getElementById('backup-tab');
const restoreTab = document.getElementById('restore-tab');
const backupPanel = document.getElementById('backup-panel');
const restorePanel = document.getElementById('restore-panel');

function showPanel(selectedTab, selectedPanel, otherTab, otherPanel) {
  selectedTab.classList.add('is-active');
  selectedTab.setAttribute('aria-selected', 'true');
  selectedPanel.classList.remove('is-hidden');
  otherTab.classList.remove('is-active');
  otherTab.setAttribute('aria-selected', 'false');
  otherPanel.classList.add('is-hidden');
}

backupTab.addEventListener('click', () => showPanel(backupTab, backupPanel, restoreTab, restorePanel));
restoreTab.addEventListener('click', () => showPanel(restoreTab, restorePanel, backupTab, backupPanel));
