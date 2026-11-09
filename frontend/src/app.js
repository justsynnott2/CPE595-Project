(() => {
  const D = window.PlannerDates, repository = window.PlannerRepository;
  const main = document.querySelector('main');
  const dialog = document.querySelector('#assignment-dialog');
  const form = document.querySelector('#assignment-form');
  const deleteDialog = document.querySelector('#delete-dialog');
  const state = { data: null, page: 'assignments', week: D.monday(new Date()), search: '', status: '', course: '', selectedDate: null, pendingDelete: null, busy: false };
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hours = n => `${Number(n.toFixed(2))}h`;
  const statuses = ['Not Started', 'In Progress', 'Done'];
  const statusClass = s => s === 'Done' ? 'done' : s === 'In Progress' ? 'progress' : 'not-started';
  const activeBlocks = () => state.data.study_blocks.filter(b => state.data.assignments.some(a => a.id === b.assignment_id && a.status !== 'Done'));
  const empty = (title, description) => `<div class="empty"><span aria-hidden="true">✳</span><h3>${title}</h3><p>${description}</p></div>`;
  let toastTimer;
  function toast(message) { const el = document.querySelector('#toast'); el.textContent = message; el.classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('visible'), 4500); }
  function heading(title, subtitle, action = '') { return `<div class="page-heading"><div><span class="eyebrow">YOUR SEMESTER, IN FOCUS</span><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`; }
  function weekControls() { return `<div class="week-controls"><button class="icon-button" data-week="-1" aria-label="Previous week">←</button><strong>${D.format(state.week)} – ${D.format(D.add(state.week, 6), { month: 'short', day: 'numeric', year: 'numeric' })}</strong><button class="icon-button" data-week="1" aria-label="Next week">→</button><button class="button secondary small" data-today>Today</button></div>`; }
  function stats() {
    const assignments = state.data.assignments, open = assignments.filter(a => a.status !== 'Done');
    const weekEnd = D.key(D.add(D.monday(new Date()), 6)), weekStart = D.key(D.monday(new Date()));
    const cards = [ ['Open assignments', open.length, 'A little progress goes a long way', '▤'], ['Due this week', open.filter(a => a.due_date >= weekStart && a.due_date <= weekEnd).length, 'Keep your next deadlines in sight', '↗'], ['Completed', assignments.filter(a => a.status === 'Done').length, 'One step closer to your goals', '✓'] ];
    return `<div class="stats">${cards.map(([label, value, note, icon]) => `<div class="stat"><div><span>${label}</span><strong>${value}</strong><small>${note}</small></div><span class="stat-icon" aria-hidden="true">${icon}</span></div>`).join('')}</div>`;
  }
  function assignmentRows() {
    const filtered = state.data.assignments.filter(a => (!state.search || `${a.title} ${a.course}`.toLowerCase().includes(state.search.toLowerCase())) && (!state.status || a.status === state.status) && (!state.course || a.course === state.course)).sort((a, b) => a.due_date.localeCompare(b.due_date) || a.id - b.id);
    if (!filtered.length) return empty('A clear desk, a clear mind.', state.data.assignments.length ? 'No assignments match your filters. Try another search or clear the filters.' : 'Add your first assignment to start planning your week.');
    return `<div class="table-scroll"><table><thead><tr><th>Assignment</th><th>Due date</th><th>Difficulty</th><th>Est. study time</th><th>Status</th><th><span class="sr-only">Actions</span></th></tr></thead><tbody>${filtered.map(a => {
      const overdue = a.status !== 'Done' && a.due_date < D.key(new Date());
      return `<tr><td><button class="assignment-title" data-edit="${a.id}">${escape(a.title)}</button><div class="assignment-meta"><span class="course-tag">${escape(a.course)}</span><span>${escape(a.type)}</span></div></td><td><span class="${overdue ? 'overdue' : ''}">${D.format(a.due_date, { month: 'short', day: 'numeric', year: 'numeric' })}</span>${overdue ? '<small class="overdue">Overdue</small>' : ''}</td><td><span class="difficulty ${a.difficulty.toLowerCase()}"><i></i>${a.difficulty}</span></td><td>${a.ai_prediction_hrs === null ? '<span class="muted">Not estimated</span>' : `<strong class="estimate">${hours(a.ai_prediction_hrs)}</strong><small class="muted">Demo estimate</small>`}</td><td><label class="sr-only" for="status-${a.id}">Status for ${escape(a.title)}</label><select id="status-${a.id}" class="status-select ${statusClass(a.status)}" data-status-id="${a.id}">${statuses.map(s => `<option${s === a.status ? ' selected' : ''}>${s}</option>`).join('')}</select></td><td><div class="row-actions"><button class="icon-button" data-edit="${a.id}" aria-label="Edit ${escape(a.title)}">✎</button><button class="icon-button delete-action" data-delete="${a.id}" aria-label="Delete ${escape(a.title)}">×</button></div></td></tr>`;
    }).join('')}</tbody></table></div>`;
  }
  function assignmentsPage() {
    return heading('Small steps. Big progress.', 'Everything on your plate, with a little more perspective.', '<button class="button primary" data-new>＋ New assignment</button>') + stats() + `<section class="panel"><div class="panel-heading"><div><h2>Your assignments <span class="count">${state.data.assignments.length}</span></h2><p>Plan the work. Make space for everything else.</p></div></div><div class="filters"><label class="search"><span aria-hidden="true">⌕</span><input id="search" placeholder="Search assignments or courses" aria-label="Search assignments or courses" value="${escape(state.search)}"></label><select id="course-filter" aria-label="Filter by course"><option value="">All courses</option>${[...new Set(state.data.assignments.map(a => a.course))].sort().map(c => `<option${c === state.course ? ' selected' : ''}>${escape(c)}</option>`).join('')}</select><select id="status-filter" aria-label="Filter by status"><option value="">All statuses</option>${statuses.map(s => `<option${s === state.status ? ' selected' : ''}>${s}</option>`).join('')}</select><button class="button subtle small" data-clear>Clear</button></div><div id="assignment-results">${assignmentRows()}</div><div class="panel-foot">Sorted by due date <span>Estimates are sample values, not live AI predictions.</span></div></section><div class="tip"><span aria-hidden="true">✦</span><div><strong>A plan that leaves room to breathe.</strong><p>See how your deadlines and study sessions fit together in the weekly calendar.</p></div><a href="#calendar">View calendar →</a></div>`;
  }
  function eventsFor(date) {
    const key = D.key(date), day = (date.getDay() + 6) % 7;
    return [
      ...state.data.assignments.filter(a => a.due_date === key).map(a => ({ kind: 'deadline', title: a.title, subtitle: `${a.course} · ${a.status === 'Done' ? 'Completed' : 'Due today'}`, id: a.id, time: '' })),
      ...state.data.commitments.filter(c => c.day_of_week === day).map(c => ({ kind: 'commitment', title: c.title, subtitle: 'Weekly commitment', time: `${c.start_time}–${c.end_time}` })),
      ...activeBlocks().filter(b => b.date === key).map(b => { const a = state.data.assignments.find(a => a.id === b.assignment_id); return { kind: 'study', title: a.title, subtitle: `${a.course} · Study session`, id: a.id, time: `${b.start_time}–${b.end_time}` }; })
    ].sort((a, b) => a.time.localeCompare(b.time));
  }
  function eventCard(event) { return `<${event.id ? 'button' : 'div'} class="calendar-event ${event.kind}" ${event.id ? `data-edit="${event.id}"` : ''}><span class="event-kind">${event.kind === 'deadline' ? 'DEADLINE' : event.kind === 'study' ? 'STUDY' : 'COMMITMENT'}</span>${event.time ? `<span class="event-time">${event.time}</span>` : ''}<strong>${escape(event.title)}</strong><small>${escape(event.subtitle)}</small></${event.id ? 'button' : 'div'}>`; }
  function calendarPage() {
    const days = Array.from({ length: 7 }, (_, i) => D.add(state.week, i));
    const selected = state.selectedDate && days.some(d => D.key(d) === state.selectedDate) ? D.parse(state.selectedDate) : null;
    return heading('Your week, at a glance.', 'Deadlines, commitments, and time to focus — all in one place.') + `<section class="panel calendar-panel"><div class="calendar-toolbar">${weekControls()}<div class="legend"><span class="deadline">Deadlines</span><span class="commitment">Commitments</span><span class="study">Study sessions</span></div></div><p class="calendar-hint">Select a day to see its agenda. Select a deadline or study session to edit its assignment.</p><div class="week-grid">${days.map(day => { const key = D.key(day), events = eventsFor(day); return `<section class="day-column ${key === D.key(new Date()) ? 'today' : ''}"><button class="day-heading ${key === state.selectedDate ? 'selected' : ''}" data-day="${key}" aria-pressed="${key === state.selectedDate}"><span>${D.format(day, { weekday: 'short' })}</span><strong>${day.getDate()}</strong>${key === D.key(new Date()) ? '<small>Today</small>' : ''}</button><div class="day-events">${events.length ? events.map(eventCard).join('') : '<p class="free-day">Room to breathe</p>'}</div></section>`; }).join('')}</div></section>${selected ? `<section class="panel day-agenda"><div class="panel-heading"><h2>${D.format(selected, { weekday: 'long', month: 'long', day: 'numeric' })}</h2></div><div class="agenda-events">${eventsFor(selected).map(eventCard).join('') || empty('Nothing planned.', 'This day has no deadlines, commitments, or study sessions.')}</div></section>` : ''}`;
  }
  function schedulePage() {
    const start = D.key(state.week), end = D.key(D.add(state.week, 6));
    const blocks = activeBlocks().filter(b => b.date >= start && b.date <= end).sort((a, b) => a.date.localeCompare(b.date) || a.start_time.localeCompare(b.start_time));
    const groups = [...new Set(blocks.map(b => b.date))];
    return heading('A little focus goes a long way.', 'A dedicated place for your study sessions, one day at a time.') + `<div class="schedule-banner"><span class="banner-icon" aria-hidden="true">✳</span><div><span class="eyebrow">YOUR FOCUS PLAN</span><h2>${hours(blocks.reduce((sum, b) => sum + D.duration(b), 0))} of planned study time</h2><p>${blocks.length} sessions this week. Take it one block at a time.</p></div><span class="sample-label">Sample schedule</span></div><section class="panel schedule-panel"><div class="calendar-toolbar">${weekControls()}<span class="muted">Grouped by date</span></div><div class="schedule-disclaimer">These are preloaded demo blocks. Creating or editing an assignment does not generate or reschedule sessions. Completed assignments are hidden from the study plan.</div>${groups.length ? groups.map(date => `<section class="schedule-day"><div class="schedule-date"><span>${D.format(date, { weekday: 'short' })}</span><strong>${D.parse(date).getDate()}</strong><small>${D.format(date, { month: 'short' })}</small></div><div class="schedule-blocks">${blocks.filter(b => b.date === date).map(b => { const a = state.data.assignments.find(a => a.id === b.assignment_id); return `<article class="study-block"><div class="block-time"><strong>${b.start_time} – ${b.end_time}</strong><span>${hours(D.duration(b))} focus session</span></div><div class="block-detail"><span class="course-tag">${escape(a.course)}</span><h3>${escape(a.title)}</h3><p>Due ${D.format(a.due_date)} · ${escape(a.type)}</p></div><button class="button secondary small" data-edit="${a.id}">View assignment</button></article>`; }).join('')}</div></section>`).join('') : empty('A little room in your week.', 'No demo study sessions for this week. Browse another week or return to today.')}</section>`;
  }
  function render() {
    document.querySelectorAll('[data-page]').forEach(a => { const active = a.dataset.page === state.page; a.classList.toggle('active', active); if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    document.querySelector('#breadcrumb').textContent = { assignments: 'Assignments', calendar: 'Calendar', schedule: 'Study Schedule' }[state.page];
    if (!state.data) return;
    main.innerHTML = ({ assignments: assignmentsPage, calendar: calendarPage, schedule: schedulePage })[state.page]() + `<div class="demo-tools"><span>Demo workspace · changes stay in this browser</span><button class="button subtle small" data-reset>Reset demo data</button></div>`;
    main.setAttribute('aria-busy', 'false');
  }
  async function load(reset = false) {
    main.setAttribute('aria-busy', 'true');
    main.innerHTML = '<div class="loading" role="status"><span class="spinner"></span>Getting your workspace ready…</div>';
    try { state.data = await repository[reset ? 'reset' : 'load'](); render(); }
    catch (error) { main.setAttribute('aria-busy', 'false'); main.innerHTML = `<section class="panel error-panel" role="alert"><h1>We couldn’t load your planner.</h1><p>${escape(error.message)}</p><button class="button primary" data-retry>Try again</button> <button class="button secondary" data-reset>Reset demo data</button></section>`; }
  }
  function openForm(id) {
    form.reset();
    const a = state.data.assignments.find(a => a.id === id);
    document.querySelector('#form-title').textContent = a ? 'Edit assignment' : 'New assignment';
    form.elements.id.value = a?.id ?? '';
    ['title', 'course', 'type', 'difficulty', 'due_date', 'status', 'actual_hrs'].forEach(k => { if (a) form.elements[k].value = a[k] ?? ''; });
    if (!a) form.elements.due_date.value = D.key(new Date());
    document.querySelector('#form-error').textContent = '';
    dialog.showModal();
  }
  function route() { state.page = ['assignments', 'calendar', 'schedule'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'assignments'; render(); }
  window.addEventListener('hashchange', route);
  main.addEventListener('click', async event => {
    const target = event.target.closest('button');
    if (!target || state.busy) return;
    if (target.hasAttribute('data-new')) openForm();
    if (target.hasAttribute('data-edit')) openForm(Number(target.dataset.edit));
    if (target.hasAttribute('data-delete')) { state.pendingDelete = Number(target.dataset.delete); const a = state.data.assignments.find(a => a.id === state.pendingDelete); document.querySelector('#delete-description').textContent = a.title; document.querySelector('#delete-error').textContent = ''; deleteDialog.showModal(); }
    if (target.hasAttribute('data-week')) { state.week = D.add(state.week, Number(target.dataset.week) * 7); state.selectedDate = null; render(); }
    if (target.hasAttribute('data-today')) { state.week = D.monday(new Date()); state.selectedDate = D.key(new Date()); render(); }
    if (target.hasAttribute('data-day')) { state.selectedDate = target.dataset.day; render(); }
    if (target.hasAttribute('data-clear')) { state.search = ''; state.status = ''; state.course = ''; render(); }
    if (target.hasAttribute('data-retry')) await load();
    if (target.hasAttribute('data-reset') && window.confirm('Replace all saved demo changes with a fresh sample week?')) { state.search = ''; state.status = ''; state.course = ''; state.week = D.monday(new Date()); state.selectedDate = null; await load(true); }
  });
  main.addEventListener('input', event => { if (event.target.id === 'search') { state.search = event.target.value; document.querySelector('#assignment-results').innerHTML = assignmentRows(); } });
  main.addEventListener('change', async event => {
    const target = event.target;
    if (target.id === 'course-filter' || target.id === 'status-filter') { state[target.id === 'course-filter' ? 'course' : 'status'] = target.value; render(); }
    if (target.hasAttribute('data-status-id')) {
      if (state.busy) { render(); return; }
      const a = state.data.assignments.find(a => a.id === Number(target.dataset.statusId));
      state.busy = true; target.disabled = true;
      try { state.data = await repository.saveAssignment({ ...a, status: target.value }); toast('Assignment status updated.'); }
      catch (error) { toast(error.message); }
      finally { state.busy = false; render(); }
    }
  });
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => { if (!state.busy) dialog.close(); }));
  [dialog, deleteDialog].forEach(el => el.addEventListener('cancel', event => { if (state.busy) event.preventDefault(); }));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (state.busy) return;
    if (!form.reportValidity()) return;
    const values = Object.fromEntries(new FormData(form));
    const assignment = { ...values, id: values.id ? Number(values.id) : undefined, actual_hrs: values.actual_hrs === '' ? null : Number(values.actual_hrs) };
    state.busy = true;
    const save = document.querySelector('#save-button'); save.disabled = true; save.textContent = 'Saving…';
    document.querySelectorAll('[data-close]').forEach(b => b.disabled = true);
    try { state.data = await repository.saveAssignment(assignment); dialog.close(); render(); toast(values.id ? 'Assignment updated.' : 'Assignment added.'); }
    catch (error) { document.querySelector('#form-error').textContent = error.message; }
    finally { state.busy = false; save.disabled = false; save.textContent = 'Save assignment'; document.querySelectorAll('[data-close]').forEach(b => b.disabled = false); }
  });
  document.querySelector('#confirm-delete').addEventListener('click', async event => {
    if (state.busy) return;
    state.busy = true; event.target.disabled = true; event.target.textContent = 'Deleting…';
    deleteDialog.querySelector('[value="cancel"]').disabled = true;
    try { state.data = await repository.deleteAssignment(state.pendingDelete); deleteDialog.close(); render(); toast('Assignment deleted.'); }
    catch (error) { document.querySelector('#delete-error').textContent = error.message; }
    finally { state.busy = false; event.target.disabled = false; event.target.textContent = 'Delete assignment'; deleteDialog.querySelector('[value="cancel"]').disabled = false; }
  });
  route(); load();
})();
