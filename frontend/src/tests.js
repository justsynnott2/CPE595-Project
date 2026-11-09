/* Run the real repository factory against isolated memory storage. */
(async () => {
  const output = document.querySelector('#results');
  const lines = [];
  const assert = (condition, message) => { if (!condition) throw new Error(message); lines.push(`PASS  ${message}`); };
  try {
    const storage = new Map();
    const localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
    // data.js is loaded as a classic script; fetch its source for an isolated test instance.
    // On file: URLs, fetch may be restricted: use the local HTTP server documented in README.
    const response = await fetch('src/data.js');
    if (!response.ok) throw new Error('Could not read repository source.');
    const source = await response.text();
    const isolated = { PlannerDates: window.PlannerDates };
    new Function('window', 'localStorage', source)(isolated, localStorage);
    const R = isolated.PlannerRepository, D = window.PlannerDates;
    assert(D.key(D.parse('2026-11-08')) === '2026-11-08', 'Date-only values retain their calendar day');
    assert(D.key(D.monday(D.parse('2026-11-08'))) === '2026-11-02', 'Sunday maps to the preceding Monday');
    assert(D.key(D.add(D.parse('2026-12-31'), 1)) === '2027-01-01', 'Week navigation crosses year boundaries');
    assert(D.duration({ start_time: '09:30', end_time: '11:00' }) === 1.5, 'Session duration handles half hours');
    const initial = await R.load();
    assert(initial.assignments.length === 6 && initial.study_blocks.length === 6, 'Demo collections load');
    const assignment = { title: '  Test assignment  ', course: 'CPE 595', type: 'Lab', difficulty: 'Medium', due_date: '2026-12-01', status: 'Not Started', actual_hrs: null };
    let data = await R.saveAssignment(assignment);
    const created = data.assignments.find(a => a.title === 'Test assignment');
    assert(created && created.ai_prediction_hrs === null, 'Create trims input and does not invent an AI estimate');
    assert((await R.load()).assignments.length === 7, 'Assignment persists across loads');
    data = await R.saveAssignment({ ...created, status: 'Done', actual_hrs: 2.5 });
    assert(data.assignments.find(a => a.id === created.id).status === 'Done', 'Status and hours can be updated');
    let rejected = false;
    try { await R.saveAssignment({ ...assignment, title: '   ' }); } catch { rejected = true; }
    assert(rejected, 'Whitespace-only titles are rejected');
    rejected = false;
    try { await R.saveAssignment({ ...assignment, due_date: '2026-02-30' }); } catch { rejected = true; }
    assert(rejected, 'Impossible dates are rejected');
    rejected = false;
    try { await R.saveAssignment({ ...assignment, actual_hrs: -1 }); } catch { rejected = true; }
    assert(rejected, 'Negative actual hours are rejected');
    data = await R.deleteAssignment(1);
    assert(!data.assignments.some(a => a.id === 1) && !data.study_blocks.some(b => b.assignment_id === 1), 'Delete removes assignment and linked study blocks');
    localStorage.setItem('studywise.demo.v1', '{broken');
    rejected = false;
    try { await R.load(); } catch { rejected = true; }
    assert(rejected, 'Corrupt saved data produces an explicit error');
    assert((await R.reset()).assignments.length === 6, 'Reset recovers from corrupt data');
    lines.push('\nAll checks passed.');
  } catch (error) { lines.push(`FAIL  ${error.message}\nServe frontend over HTTP if file: fetch is blocked. See README.`); }
  output.textContent = lines.join('\n');
})();
