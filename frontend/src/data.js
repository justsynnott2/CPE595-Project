/* Replace PlannerRepository with an HTTP adapter later; views never access storage. */
window.PlannerRepository = (() => {
  const D = window.PlannerDates;
  const STORAGE_KEY = 'studywise.demo.v1';
  const types = ['Homework', 'Lab', 'Reading', 'Exam', 'Project'];
  const statuses = ['Not Started', 'In Progress', 'Done'];
  function seed() {
    const week = D.monday(new Date());
    const date = offset => D.key(D.add(week, offset));
    return {
      assignments: [
        { id: 1, course: 'CPE 595', title: 'Neural networks problem set', type: 'Homework', difficulty: 'Hard', due_date: date(2), status: 'In Progress', ai_prediction_hrs: 4.5, actual_hrs: 1.5 },
        { id: 2, course: 'CS 546', title: 'Build a REST API', type: 'Project', difficulty: 'Hard', due_date: date(4), status: 'Not Started', ai_prediction_hrs: 6, actual_hrs: null },
        { id: 3, course: 'CPE 593', title: 'Graph algorithms lab', type: 'Lab', difficulty: 'Medium', due_date: date(3), status: 'In Progress', ai_prediction_hrs: 3, actual_hrs: 1 },
        { id: 4, course: 'CPE 595', title: 'Read: attention mechanisms', type: 'Reading', difficulty: 'Medium', due_date: date(6), status: 'Not Started', ai_prediction_hrs: 2, actual_hrs: null },
        { id: 5, course: 'CS 546', title: 'Database schema review', type: 'Homework', difficulty: 'Easy', due_date: date(1), status: 'Done', ai_prediction_hrs: 1.5, actual_hrs: 1.25 },
        { id: 6, course: 'CPE 593', title: 'Midterm practice problems', type: 'Exam', difficulty: 'Hard', due_date: date(9), status: 'Not Started', ai_prediction_hrs: 5, actual_hrs: null }
      ],
      commitments: [
        { id: 1, title: 'CPE 595 · Machine Learning', day_of_week: 0, start_time: '10:00', end_time: '11:30' },
        { id: 2, title: 'CS 546 · Web Programming', day_of_week: 2, start_time: '13:00', end_time: '14:30' },
        { id: 3, title: 'CPE 593 · Algorithms', day_of_week: 3, start_time: '10:00', end_time: '11:30' },
        { id: 4, title: 'Campus work shift', day_of_week: 4, start_time: '09:00', end_time: '12:00' }
      ],
      study_blocks: [
        { id: 1, assignment_id: 1, date: date(0), start_time: '14:00', end_time: '15:30' },
        { id: 2, assignment_id: 1, date: date(1), start_time: '09:00', end_time: '10:30' },
        { id: 3, assignment_id: 2, date: date(1), start_time: '14:00', end_time: '16:00' },
        { id: 4, assignment_id: 3, date: date(2), start_time: '10:00', end_time: '12:00' },
        { id: 5, assignment_id: 2, date: date(3), start_time: '14:00', end_time: '16:00' },
        { id: 6, assignment_id: 4, date: date(5), start_time: '10:00', end_time: '12:00' }
      ]
    };
  }
  function validate(a) {
    if (!a.title?.trim() || !a.course?.trim()) throw new Error('Enter an assignment title and course.');
    if (a.title.trim().length > 120 || a.course.trim().length > 60) throw new Error('The title or course is too long.');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(a.due_date) || Number.isNaN(D.parse(a.due_date).getTime()) || D.key(D.parse(a.due_date)) !== a.due_date) throw new Error('Choose a valid due date.');
    if (!types.includes(a.type) || !statuses.includes(a.status) || !['Easy', 'Medium', 'Hard'].includes(a.difficulty)) throw new Error('Choose valid assignment options.');
    if (a.actual_hrs !== null && (!Number.isFinite(a.actual_hrs) || a.actual_hrs < 0 || a.actual_hrs > 1000)) throw new Error('Actual hours must be between 0 and 1,000.');
  }
  function read() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return seed();
    let value;
    try { value = JSON.parse(raw); } catch { throw new Error('Saved demo data could not be read. Use Reset demo data to recover.'); }
    if (!value || !['assignments', 'commitments', 'study_blocks'].every(k => Array.isArray(value[k]))) throw new Error('Saved demo data is invalid. Use Reset demo data to recover.');
    value.assignments.forEach(validate);
    return value;
  }
  const copy = value => JSON.parse(JSON.stringify(value));
  async function operation(fn) {
    await new Promise(resolve => setTimeout(resolve, 180));
    try { return copy(fn()); } catch (error) {
      if (error.name === 'QuotaExceededError' || error.name === 'SecurityError') throw new Error('Browser storage is unavailable or full. Allow local storage and retry.');
      throw error;
    }
  }
  return {
    load: () => operation(() => { const data = read(); if (!localStorage.getItem(STORAGE_KEY)) localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); return data; }),
    saveAssignment: assignment => operation(() => {
      validate(assignment);
      const data = read();
      const existing = data.assignments.find(a => a.id === assignment.id);
      if (assignment.id && !existing) throw new Error('This assignment no longer exists. Refresh and try again.');
      const saved = { ...existing, ...assignment, title: assignment.title.trim(), course: assignment.course.trim(), id: existing?.id ?? Math.max(0, ...data.assignments.map(a => a.id)) + 1, ai_prediction_hrs: existing?.ai_prediction_hrs ?? null };
      data.assignments = existing ? data.assignments.map(a => a.id === saved.id ? saved : a) : [...data.assignments, saved];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      return data;
    }),
    deleteAssignment: id => operation(() => {
      const data = read();
      data.assignments = data.assignments.filter(a => a.id !== id);
      data.study_blocks = data.study_blocks.filter(b => b.assignment_id !== id);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      return data;
    }),
    reset: () => operation(() => { const data = seed(); localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); return data; })
  };
})();
