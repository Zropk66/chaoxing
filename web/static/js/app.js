let activeAccountId = null;
let currentFullConfig = {};
let currentPendingPromptId = null;
let currentSelectedAnswers = [];
let qrPollTimer = null;

function pushToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const card = document.createElement('div');
  card.className = 'toast-card';
  card.textContent = message;
  container.appendChild(card);
  setTimeout(() => card.classList.add('show'), 10);
  setTimeout(() => {
    card.classList.remove('show');
    setTimeout(() => card.remove(), 300);
  }, 3500);
}

function appendLog(timestamp, level, message) {
  const consoleEl = document.getElementById('logConsole');
  if (!consoleEl) return;
  const line = document.createElement('div');
  line.className = 'log-line';
  const timeSpan = document.createElement('span');
  timeSpan.className = 'log-time';
  timeSpan.textContent = `[${timestamp}]`;
  const levelSpan = document.createElement('span');
  levelSpan.className = `log-level-${level.toLowerCase()}`;
  levelSpan.textContent = `[${level}] `;
  const msgSpan = document.createElement('span');
  msgSpan.textContent = message;

  line.appendChild(timeSpan);
  line.appendChild(levelSpan);
  line.appendChild(msgSpan);
  consoleEl.appendChild(line);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

async function loadAccounts() {
  try {
    const data = await API.fetchAccounts();
    const dropdown = document.getElementById('accountDropdownList');
    if (!dropdown) return;
    dropdown.innerHTML = '';
    activeAccountId = data.active_account;

    const currentNameEl = document.getElementById('currentAccountName');
    if (currentNameEl) {
      currentNameEl.textContent = activeAccountId || '未登录账号';
    }

    data.accounts.forEach(acc => {
      const item = document.createElement('div');
      item.className = `dropdown-item ${acc.active ? 'active' : ''}`;
      item.innerHTML = `
        <div>
          <div style="font-weight: 600;">${acc.username}</div>
          <div style="font-size: 0.7rem; color: var(--text-dim);">${acc.file}</div>
        </div>
        ${acc.active ? '<span class="badge badge-blue">当前</span>' : ''}
      `;
      item.onclick = async () => {
        await API.switchAccount(acc.id);
        toggleAccountDropdown(false);
        pushToast(`已切换至账号: ${acc.username}`);
        await loadAccounts();
        await loadCourses();
      };
      dropdown.appendChild(item);
    });
  } catch (e) {
    console.error('加载账号失败', e);
  }
}

function toggleAccountDropdown(show) {
  const el = document.getElementById('accountDropdown');
  if (!el) return;
  if (typeof show === 'boolean') {
    el.classList.toggle('show', show);
  } else {
    el.classList.toggle('show');
  }
}

function openLoginModal() {
  toggleAccountDropdown(false);
  const modal = document.getElementById('loginModalOverlay');
  if (modal) modal.classList.add('show');
  switchLoginTab('QR');
}

function closeLoginModal() {
  const modal = document.getElementById('loginModalOverlay');
  if (modal) modal.classList.remove('show');
  if (qrPollTimer) {
    clearInterval(qrPollTimer);
    qrPollTimer = null;
  }
}

function switchLoginTab(tab) {
  const tabQr = document.getElementById('tabContentQr');
  const tabPwd = document.getElementById('tabContentPwd');
  const btnQr = document.getElementById('tabBtnQr');
  const btnPwd = document.getElementById('tabBtnPwd');

  if (tab === 'QR') {
    if (tabQr) tabQr.style.display = 'block';
    if (tabPwd) tabPwd.style.display = 'none';
    if (btnQr) btnQr.classList.add('active');
    if (btnPwd) btnPwd.classList.remove('active');
    startQrSession();
  } else {
    if (tabQr) tabQr.style.display = 'none';
    if (tabPwd) tabPwd.style.display = 'block';
    if (btnQr) btnQr.classList.remove('active');
    if (btnPwd) btnPwd.classList.add('active');
    if (qrPollTimer) {
      clearInterval(qrPollTimer);
      qrPollTimer = null;
    }
  }
}

async function startQrSession() {
  if (qrPollTimer) clearInterval(qrPollTimer);
  const imgEl = document.getElementById('loginQrImage');
  const tipEl = document.getElementById('loginQrTip');
  if (tipEl) tipEl.textContent = '正在拉取二维码...';

  try {
    const res = await API.createQrSession();
    if (res.status && res.session_id) {
      if (imgEl) imgEl.src = res.qr_url;
      if (tipEl) tipEl.textContent = '请打开学习通 APP 扫码登录';
      qrPollTimer = setInterval(async () => {
        const poll = await API.pollQrStatus(res.session_id);
        if (poll.status === 'CONFIRMED' && tipEl) {
          tipEl.textContent = '已扫码，请在手机端点击确认登录';
        } else if (poll.status === 'SUCCESS') {
          clearInterval(qrPollTimer);
          pushToast('扫码登录成功');
          closeLoginModal();
          await loadAccounts();
        } else if (poll.status === 'EXPIRED') {
          clearInterval(qrPollTimer);
          if (tipEl) tipEl.textContent = '二维码已失效，点击重新加载';
        }
      }, 1500);
    }
  } catch (e) {
    if (tipEl) tipEl.textContent = '生成二维码失败，请检查网络';
  }
}

async function handlePasswordLogin(e) {
  e.preventDefault();
  const u = document.getElementById('pwdUsername')?.value;
  const p = document.getElementById('pwdPassword')?.value;
  if (!u || !p) return;
  try {
    const res = await API.loginWithPassword(u, p);
    if (res.status === 'success') {
      pushToast('密码登录成功');
      closeLoginModal();
      await loadAccounts();
    } else {
      pushToast(`登录失败: ${res.msg || '凭据错误'}`, 'error');
    }
  } catch (err) {
    pushToast('密码登录异常', 'error');
  }
}

async function loadCourses() {
  const tbody = document.getElementById('courseTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 2rem;">加载中...</td></tr>';
  try {
    const res = await API.fetchCourses();
    const courses = res.courses || [];
    const selected = new Set(res.selected_ids || []);
    if (courses.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 2rem;">暂无课程或尚未载入会话凭据</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    courses.forEach(c => {
      const isChecked = selected.has(String(c.courseId));
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input type="checkbox" class="course-cb" value="${c.courseId}" ${isChecked ? 'checked' : ''} onchange="updateSelectedCount()"></td>
        <td style="font-weight: 500;">${c.title}</td>
        <td style="font-family: var(--font-mono); color: var(--text-muted);">${c.courseId}</td>
        <td>${c.clazzId || '-'}</td>
        <td>${c.teacher || '-'}</td>
        <td><span class="badge ${c.progress >= 100 ? 'badge-green' : 'badge-blue'}">${c.progress || 0}%</span></td>
      `;
      tbody.appendChild(tr);
    });
    updateSelectedCount();
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--accent-danger); padding: 2rem;">获取课程失败</td></tr>';
  }
}

function updateSelectedCount() {
  const cbs = document.querySelectorAll('.course-cb:checked');
  const countEl = document.getElementById('selectedCourseCount');
  if (countEl) countEl.textContent = String(cbs.length);
}

function selectAllCourses(checked) {
  document.querySelectorAll('.course-cb').forEach(cb => {
    cb.checked = checked;
  });
  updateSelectedCount();
}

async function saveSelectedCourses() {
  const cbs = document.querySelectorAll('.course-cb:checked');
  const ids = Array.from(cbs).map(cb => cb.value);
  try {
    await API.saveCourseList(ids);
    pushToast(`已保存 ${ids.length} 门课程至当前账号配置`);
  } catch (e) {
    pushToast('保存课程失败', 'error');
  }
}

async function openSettingsModal() {
  const modal = document.getElementById('settingsModalOverlay');
  if (!modal) return;
  modal.classList.add('show');
  switchSettingsTab('common');
  try {
    currentFullConfig = await API.fetchFullConfig();
    populateSettingsForm(currentFullConfig);
  } catch (e) {
    pushToast('读取配置失败', 'error');
  }
}

function closeSettingsModal() {
  const modal = document.getElementById('settingsModalOverlay');
  if (modal) modal.classList.remove('show');
}

function switchSettingsTab(tabName) {
  document.querySelectorAll('.settings-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });
  document.querySelectorAll('.settings-tab-pane').forEach(pane => {
    pane.style.display = (pane.dataset.pane === tabName) ? 'block' : 'none';
  });
}

function populateSettingsForm(cfg) {
  const common = cfg.common || {};
  const tiku = cfg.tiku || {};
  const notif = cfg.notification || {};

  setVal('cfg_jobs', common.jobs ?? 4);
  setVal('cfg_notopen_action', common.notopen_action ?? 'retry');
  setVal('cfg_retry_interval', common.retry_interval ?? 1.0);
  setCheck('cfg_work_redo_enabled', !!common.work_redo_enabled);
  setVal('cfg_work_max_retries', common.work_max_retries ?? 3);
  setCheck('cfg_add_learning_count', !!common.add_learning_count);
  setVal('cfg_target_count', common.target_count ?? 100);

  setVal('cfg_provider', tiku.provider ?? 'TikuYanxi');
  setCheck('cfg_submit', !!tiku.submit);
  setVal('cfg_cover_rate', tiku.cover_rate ?? 0.9);
  setVal('cfg_delay', tiku.delay ?? 1.0);
  setCheck('cfg_check_llm', !!tiku.check_llm_connection);

  setVal('cfg_tokens', tiku.tokens ?? '');
  setCheck('cfg_like_search', !!tiku.likeapi_search);
  setCheck('cfg_like_vision', !!tiku.likeapi_vision);
  setVal('cfg_like_model', tiku.likeapi_model ?? 'glm-4.5-air');
  setVal('cfg_tiku_url', tiku.url ?? '');
  setVal('cfg_go_auth', tiku.go_authorization ?? '');
  setVal('cfg_go_interval', tiku.go_min_interval ?? 1.0);

  setVal('cfg_ai_endpoint', tiku.endpoint ?? '');
  setVal('cfg_ai_key', tiku.key ?? '');
  setVal('cfg_ai_model', tiku.model ?? '');
  setVal('cfg_sf_key', tiku.siliconflow_key ?? '');
  setVal('cfg_sf_model', tiku.siliconflow_model ?? 'deepseek-ai/DeepSeek-R1');

  setVal('cfg_manual_mode', tiku.manual_mode_default ?? 'batch');
  setVal('cfg_manual_sep', tiku.manual_mode_separator ?? ';');
  setVal('cfg_true_list', tiku.true_list ?? '正确,对,√,是');
  setVal('cfg_false_list', tiku.false_list ?? '错误,错,×,否,不对,不正确');

  setVal('cfg_notif_provider', notif.provider ?? 'ServerChan');
  setVal('cfg_notif_url', notif.url ?? '');
  setVal('cfg_notif_tg_id', notif.tg_chat_id ?? '');
}

function readSettingsForm() {
  return {
    common: {
      jobs: parseInt(getVal('cfg_jobs'), 10) || 4,
      notopen_action: getVal('cfg_notopen_action'),
      retry_interval: parseFloat(getVal('cfg_retry_interval')) || 1.0,
      work_redo_enabled: getCheck('cfg_work_redo_enabled'),
      work_max_retries: parseInt(getVal('cfg_work_max_retries'), 10) || 3,
      add_learning_count: getCheck('cfg_add_learning_count'),
      target_count: parseInt(getVal('cfg_target_count'), 10) || 100
    },
    tiku: {
      provider: getVal('cfg_provider'),
      submit: getCheck('cfg_submit'),
      cover_rate: parseFloat(getVal('cfg_cover_rate')) || 0.9,
      delay: parseFloat(getVal('cfg_delay')) || 1.0,
      check_llm_connection: getCheck('cfg_check_llm'),
      tokens: getVal('cfg_tokens'),
      likeapi_search: getCheck('cfg_like_search'),
      likeapi_vision: getCheck('cfg_like_vision'),
      likeapi_model: getVal('cfg_like_model'),
      url: getVal('cfg_tiku_url'),
      go_authorization: getVal('cfg_go_auth'),
      go_min_interval: parseFloat(getVal('cfg_go_interval')) || 1.0,
      endpoint: getVal('cfg_ai_endpoint'),
      key: getVal('cfg_ai_key'),
      model: getVal('cfg_ai_model'),
      siliconflow_key: getVal('cfg_sf_key'),
      siliconflow_model: getVal('cfg_sf_model'),
      manual_mode_default: getVal('cfg_manual_mode'),
      manual_mode_separator: getVal('cfg_manual_sep'),
      true_list: getVal('cfg_true_list'),
      false_list: getVal('cfg_false_list')
    },
    notification: {
      provider: getVal('cfg_notif_provider'),
      url: getVal('cfg_notif_url'),
      tg_chat_id: getVal('cfg_notif_tg_id')
    }
  };
}

async function saveSettings() {
  const data = readSettingsForm();
  try {
    await API.saveFullConfig(data);
    pushToast('配置已成功保存并生效');
    closeSettingsModal();
  } catch (e) {
    pushToast('保存配置异常', 'error');
  }
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}
function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}
function setCheck(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = val;
}
function getCheck(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function handleManualQuestion(data) {
  currentPendingPromptId = data.prompt_id;
  currentSelectedAnswers = [];
  const modal = document.getElementById('manualQuizModalOverlay');
  if (!modal) return;

  const titleEl = document.getElementById('quizQuestionTitle');
  const typeEl = document.getElementById('quizTypeBadge');
  const optionsEl = document.getElementById('quizOptionsContainer');
  const textInputEl = document.getElementById('quizTextInputWrap');

  if (titleEl) titleEl.textContent = data.title || '题目';
  if (typeEl) typeEl.textContent = data.type_display || data.type || '单选题';
  if (optionsEl) optionsEl.innerHTML = '';

  const qType = data.type || 'single';
  const options = data.options || [];

  if (qType === 'judgement') {
    if (textInputEl) textInputEl.style.display = 'none';
    ['正确', '错误'].forEach(opt => {
      const card = document.createElement('div');
      card.className = 'quiz-option-card';
      card.textContent = opt;
      card.onclick = () => {
        document.querySelectorAll('.quiz-option-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        currentSelectedAnswers = [opt];
      };
      optionsEl.appendChild(card);
    });
  } else if (options.length > 0) {
    if (textInputEl) textInputEl.style.display = 'none';
    options.forEach(opt => {
      const card = document.createElement('div');
      card.className = 'quiz-option-card';
      card.textContent = opt;
      const letter = opt.trim().substring(0, 1).toUpperCase();
      card.onclick = () => {
        if (qType === 'multiple') {
          card.classList.toggle('selected');
          if (card.classList.contains('selected')) {
            currentSelectedAnswers.push(letter);
          } else {
            currentSelectedAnswers = currentSelectedAnswers.filter(x => x !== letter);
          }
        } else {
          document.querySelectorAll('.quiz-option-card').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          currentSelectedAnswers = [letter];
        }
      };
      optionsEl.appendChild(card);
    });
  } else {
    if (textInputEl) textInputEl.style.display = 'block';
  }

  modal.classList.add('show');
}

async function submitCurrentQuizAnswer() {
  if (!currentPendingPromptId) return;
  let ans = '';
  const textInput = document.getElementById('quizAnswerInput');
  if (textInput && textInput.parentElement && textInput.parentElement.style.display !== 'none') {
    ans = textInput.value.trim();
  } else {
    ans = currentSelectedAnswers.join('');
  }

  try {
    await API.submitManualAnswer(currentPendingPromptId, ans);
    closeManualQuizModal();
    pushToast(`已提交答案: ${ans || '[空]'}`);
  } catch (e) {
    pushToast('提交作答失败', 'error');
  }
}

async function skipCurrentQuiz() {
  if (!currentPendingPromptId) return;
  try {
    await API.skipManualAnswer(currentPendingPromptId);
    closeManualQuizModal();
    pushToast('已跳过此题');
  } catch (e) {
    pushToast('跳过操作失败', 'error');
  }
}

function closeManualQuizModal() {
  const modal = document.getElementById('manualQuizModalOverlay');
  if (modal) modal.classList.remove('show');
  currentPendingPromptId = null;
  currentSelectedAnswers = [];
}

function initSSE() {
  const evtSource = new EventSource('/api/events');

  evtSource.addEventListener('STATUS_UPDATE', e => {
    try {
      const data = JSON.parse(e.data);
      updateDashboardStats(data);
    } catch (err) {}
  });

  evtSource.addEventListener('LOG_APPEND', e => {
    try {
      const data = JSON.parse(e.data);
      appendLog(data.timestamp, data.level, data.message);
    } catch (err) {}
  });

  evtSource.addEventListener('MANUAL_QUESTION_REQUEST', e => {
    try {
      const data = JSON.parse(e.data);
      handleManualQuestion(data);
    } catch (err) {}
  });

  evtSource.addEventListener('MANUAL_QUESTION_RESOLVED', () => {
    closeManualQuizModal();
  });
}

function updateDashboardStats(data) {
  const pEl = document.getElementById('statProgress');
  const tEl = document.getElementById('statTasks');
  const qEl = document.getElementById('statQuiz');
  const wContainer = document.getElementById('workersContainer');

  if (pEl) pEl.textContent = `${data.overall_progress || 0}%`;
  if (tEl) tEl.textContent = `${data.completed_jobs || 0} / ${data.total_jobs || 0}`;
  if (qEl) qEl.textContent = `${data.passed_tests || 0}`;

  if (wContainer && data.workers) {
    wContainer.innerHTML = '';
    data.workers.forEach(w => {
      const card = document.createElement('div');
      card.className = 'worker-card';
      const pct = w.duration > 0 ? Math.min(100, Math.round((w.position / w.duration) * 100)) : 0;
      card.innerHTML = `
        <div class="worker-header">
          <div class="worker-title">${w.id}: ${w.chapter || '待命'}</div>
          <span class="badge ${w.status === 'PLAYING' ? 'badge-blue' : 'badge-gray'}">${w.speed || 1.0}x</span>
        </div>
        <div class="progress-bar-wrap">
          <div class="progress-fill" style="width: ${pct}%;"></div>
        </div>
        <div style="font-size: 0.7rem; color: var(--text-dim); display: flex; justify-content: space-between;">
          <span>${w.position || 0}s / ${w.duration || 0}s</span>
          <span>${pct}%</span>
        </div>
      `;
      wContainer.appendChild(card);
    });
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadAccounts();
  await loadCourses();
  initSSE();

  const searchInput = document.getElementById('courseSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', e => {
      const kw = e.target.value.toLowerCase();
      document.querySelectorAll('#courseTableBody tr').forEach(tr => {
        tr.style.display = tr.textContent.toLowerCase().includes(kw) ? '' : 'none';
      });
    });
  }

  const speedSlider = document.getElementById('globalSpeedSlider');
  if (speedSlider) {
    speedSlider.addEventListener('change', async e => {
      const sp = parseFloat(e.target.value);
      await API.setGlobalSpeed(sp);
      pushToast(`全局倍速已更新为 ${sp}x`);
    });
  }
});
