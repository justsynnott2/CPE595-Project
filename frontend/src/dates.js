/* Local calendar dates: never parse YYYY-MM-DD as a UTC timestamp. */
window.PlannerDates = (() => {
  const parse = value => { const [y, m, d] = value.split('-').map(Number); return new Date(y, m - 1, d); };
  const key = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const add = (date, days) => { const result = new Date(date); result.setDate(result.getDate() + days); return result; };
  const monday = date => add(date, -((date.getDay() + 6) % 7));
  const format = (value, options = { month: 'short', day: 'numeric' }) => (typeof value === 'string' ? parse(value) : value).toLocaleDateString(undefined, options);
  const duration = block => { const minutes = t => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5)); return (minutes(block.end_time) - minutes(block.start_time)) / 60; };
  return { parse, key, add, monday, format, duration };
})();
