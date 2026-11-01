/* Kiểm thử giao diện theo vai người dùng, chạy trong trình duyệt thật.
 *
 * Cách chạy:
 *   1. ACCESS_CODE=thu CLASSROOM_MEMORY=1 E2E=1 python scripts/dev_server.py 3111
 *   2. Mở http://localhost:3111 rồi dán vào console:
 *        document.head.append(Object.assign(document.createElement('script'), { src: '/__e2e.js' }));
 *        await runE2E();
 *
 * Kịch bản dùng dữ liệu "Chạy thử" nên không cần camera, khóa API hay ảnh. Kết quả là { passed, failed: [...] }.
 * Chạy ở cả khung máy tính và khung điện thoại (390 px).
 */
window.runE2E = async function runE2E() {
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const failed = []; let passed = 0;
  const check = (name, cond, extra) => { if (cond) passed++; else failed.push(name + (extra !== undefined ? ' → ' + JSON.stringify(extra) : '')); };
  const until = async (cond, ms = 6000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (cond()) return true; await sleep(60); } return false; };
  const setv = (id, v) => { $(id).value = v; $(id).dispatchEvent(new Event('change')); };
  const realFetch = window.fetch;
  const visible = (id) => !$(id).hidden && !$(id).closest('[hidden]');
  const view = (name) => { $('tab-' + name).click(); };
  const idle = async () => { await until(() => !$('btn-demo').disabled); await sleep(150); };
  const demo = async (name) => { view('them'); setv('scenario', name); $('btn-demo').click(); await idle(); };
  const stars = () => Number($('stars-count').textContent);
  window.confirm = () => { throw new Error('không được dùng hộp xác nhận mặc định của trình duyệt'); };
  const firstVisit = !localStorage.getItem('cv_howto_hidden');   // lời chào chỉ kiểm tra được trên hồ sơ trình duyệt mới
  if (!$('class-leave').hidden) $('class-leave').click();         // phiên trình duyệt giữ mã lớp của lần chạy trước: rời lớp để trang về trạng thái sạch
  localStorage.clear(); sessionStorage.clear(); location.hash = '#/ghep';
  $('speak').checked = false; $('fx').checked = false;     // tắt giọng đọc và pháo giấy cho kịch bản
  view('ghep');
  const csp = []; document.addEventListener('securitypolicyviolation', (e) => csp.push(e.violatedDirective + ' ' + e.blockedURI));

  /* ---------- Vai 1: học sinh lớp 7 lần đầu dùng ---------- */
  if (firstVisit) check('thấy lời chào lần đầu', visible('welcome'));
  else $('welcome').hidden = false;                              // hồ sơ cũ: bật lại để vẫn kiểm tra nút đóng
  check('KIỂM TRA khóa và có lời giải thích vì sao', $('btn-check').disabled && visible('check-hint'));
  check('thanh bước đang ở bước 1', $('step-1').classList.contains('on'));
  $('welcome-close').click();
  check('ẩn lời chào và nhớ lựa chọn', !visible('welcome') && JSON.parse(localStorage.getItem('cv_howto_hidden')) === true);
  const expected = {
    'Nước, ghép đúng': 'ok', 'Nước, sai liên kết': 'close', 'Ghép dở (H–O)': 'close', 'Thừa một thẻ N': 'close',
    'CO2, ghép đúng': 'ok', 'Đimetyl ete': 'ok', 'Hai cụm rời nhau': 'close', 'Ảnh chưa rõ': 'warn', 'Không có thẻ': 'warn',
  };
  for (const [name, cls] of Object.entries(expected)) {
    await demo(name);
    check('chạy thử chuyển về thẻ Ghép thẻ: ' + name, visible('view-ghep'));
    check('tình huống ' + name + ' tô màu ' + cls, $('result').classList.contains(cls), $('result').className);
    check('tình huống ' + name + ' có tiêu đề ngắn', $('headline').textContent.length > 3 && $('headline').textContent.length <= 40, $('headline').textContent);
    check('thanh bước nhảy sang bước 3', $('step-3').classList.contains('on'));
  }
  await demo('Nước, ghép đúng');
  check('đúng thì khen và nói tên chất', $('headline').textContent === 'Chính xác!' && /nước/.test($('sub').textContent), [$('headline').textContent, $('sub').textContent]);
  check('công thức có chỉ số dưới', $('sub').querySelectorAll('sub').length === 1 && $('sub').querySelector('sub').textContent === '2');
  check('hiện phân tử khối', /Phân tử khối 18/.test($('facts').textContent), $('facts').textContent);
  check('hiện các thẻ nhìn thấy (ba lục giác)', $('cards-seen').children.length === 3 && !$('cards-seen').hidden);
  check('con dấu tích khi đúng', /seal-ok/.test($('seal').src));
  check('thẻ nguyên tố có màu CPK riêng', new Set([...$('cards-seen').children].map((c) => c.style.getPropertyValue('--c'))).size === 2);
  await demo('Nước, sai liên kết');
  check('sai thì khích lệ, chỉ cách sửa', $('headline').textContent === 'Gần đúng rồi!' && /Thử nối H–O/.test($('sub').textContent), $('sub').textContent);
  check('Vì sao? có giải thích, mặc định thu gọn', !$('why').hidden && !$('why').open && $('why-list').children.length >= 3);
  check('con dấu xoay lại khi gần đúng', /seal-close/.test($('seal').src));
  await demo('Ghép dở (H–O)');
  check('gợi ý hiện nút Đúng/Không phải', visible('suggest'));
  $('sg-no').click(); $('sg-no').click(); $('sg-no').click();
  check('hết gợi ý thì ẩn hộp gợi ý', !visible('suggest') && $('headline').textContent === 'Hết gợi ý rồi', $('headline').textContent);
  await demo('Không có thẻ');
  check('không có thẻ thì nhắc nhẹ nhàng', /Chưa thấy thẻ nào/.test($('headline').textContent));

  /* ---------- Vai 2: học sinh lớp 8, thử thách, sao, huy hiệu ---------- */
  view('thuthach');
  check('hiện 11 ô nhiệm vụ', $('deck-grid').children.length === 11, $('deck-grid').children.length);
  [...$('grade-chips').children].find((b) => b.textContent === 'Lớp 8').click();
  check('lọc lớp 8 còn 3 ô', $('deck-grid').children.length === 3, $('deck-grid').children.length);
  [...$('grade-chips').children].find((b) => b.textContent === 'Tất cả').click();
  const tile = [...$('deck-grid').children].find((b) => b.dataset.deck === 'Khởi động');
  check('ô nhiệm vụ có tên truy cập đầy đủ', /Khởi động: 0 trên 6 chất, 0 sao/.test(tile.getAttribute('aria-label')), tile.getAttribute('aria-label'));
  tile.click(); await until(() => visible('mission'));
  check('bắt đầu nhiệm vụ thì sang thẻ Ghép thẻ và hiện nhiệm vụ', visible('view-ghep') && visible('mission') && /Câu 1\/6/.test($('ch-task').textContent), $('ch-task').textContent);
  check('có 6 chấm tiến độ, chấm đầu là câu hiện tại', $('mission-dots').children.length === 6 && $('mission-dots').children[0].className === 'now');
  $('ch-hint').click(); await until(() => /Gợi ý 1\/3/.test($('headline').textContent));
  check('gợi ý mức 1', /Gợi ý 1\/3/.test($('headline').textContent), $('headline').textContent);
  $('ch-skip').click(); $('ch-skip').click();
  check('bỏ qua hai câu, tới câu 3 (nước)', /Câu 3\/6/.test($('ch-task').textContent) && $('mission-dots').children[0].className === 'skip', $('ch-task').textContent);
  const before = stars();
  await demo('Nước, ghép đúng');
  check('giải đúng thì khen', $('headline').textContent === 'Đúng rồi!' && $('result').classList.contains('ok'), $('headline').textContent);
  check('thưởng 3 sao (không dùng gợi ý ở câu này)', stars() - before === 3 || stars() === 3, [before, stars()]);
  check('nhận huy hiệu đầu tiên', progressHas('first'));
  $('tab-thuthach').click();
  [...$('deck-grid').children].find((b) => b.dataset.deck === 'Lớp 8: Oxit').click(); await until(() => $('confirm-dialog').open);
  check('đổi nhiệm vụ giữa chừng thì hỏi xác nhận trong trang', $('confirm-dialog').open);
  $('confirm-no').click(); await sleep(200);
  check('hủy thì giữ nhiệm vụ cũ', /Khởi động/.test($('mission-eyebrow').textContent), $('mission-eyebrow').textContent);
  view('ghep');
  for (let i = 0; i < 3; i++) $('ch-skip').click();
  check('hết bộ đề thì đổi nút thành Chọn nhiệm vụ khác', $('ch-end').textContent === 'Chọn nhiệm vụ khác' && $('ch-hint').hidden);
  $('ch-end').click(); await until(() => visible('view-thuthach'));
  check('xong thì về thẻ Thử thách', visible('view-thuthach'));
  const solvedTile = [...$('deck-grid').children].find((b) => b.dataset.deck === 'Khởi động');
  check('ô nhiệm vụ nhớ tiến độ', /1 trên 6 chất, 3 sao/.test(solvedTile.getAttribute('aria-label')), solvedTile.getAttribute('aria-label'));

  /* ---------- Vai 3: cân bằng phương trình ---------- */
  view('canbang');
  setv('eq-select', '8');
  check('mỗi hệ số có nút tăng giảm', document.querySelectorAll('#eq-form .step').length === 8);
  const rows = () => [...$('eq-counts').tBodies[0].rows].map((r) => r.className);
  check('bảng đếm nguyên tử báo đúng chỗ lệch lúc đầu (C, O lệch, H đã bằng)', rows().join() === 'bad,ok,bad', rows());
  $('eq-form').querySelectorAll('.step')[1].click();
  check('nút + tăng hệ số và bảng cập nhật', $('eq-c0').value === '2');
  $('eq-form').querySelectorAll('.step')[0].click(); $('eq-form').querySelectorAll('.step')[0].click();
  check('hệ số không giảm dưới 1', $('eq-c0').value === '1');
  $('eq-c0').value = ''; $('eq-check').click(); await sleep(150);
  check('ô trống được báo đích danh', /Ô số 1 đang trống/.test($('eq-msg').textContent) && $('eq-c0').getAttribute('aria-invalid') === 'true', $('eq-msg').textContent);
  $('eq-c0').value = '1.5'; $('eq-check').click(); await sleep(150);
  check('số thập phân bị từ chối', /số nguyên/.test($('eq-msg').textContent));
  $('eq-c0').value = '21'; $('eq-check').click(); await sleep(150);
  check('ngoài khoảng bị từ chối', /từ 1 đến 20/.test($('eq-msg').textContent));
  setv('eq-select', '8');
  $('eq-check').click(); await until(() => /Chưa cân bằng/.test($('eq-msg').textContent));
  check('chưa cân bằng thì nêu nguyên tố lệch', /Chưa cân bằng/.test($('eq-msg').textContent) && $('eq-msg').classList.contains('bad'));
  const eqCount = $('eq-select').options.length;
  let eqOk = 0;
  const starsBefore = stars();
  for (let i = 0; i < eqCount; i++) {
    setv('eq-select', String(i));
    $('eq-reveal').click(); await until(() => /^Đáp án/.test($('eq-msg').textContent));
    $('eq-check').click(); await until(() => /Chính xác|Chưa cân bằng|Đã cân bằng/.test($('eq-msg').textContent));
    if ($('eq-msg').classList.contains('ok') && !$('eq-next').hidden) eqOk++;
  }
  check('mọi phương trình: xem đáp án rồi kiểm tra đều đúng', eqOk === eqCount, { eqOk, eqCount });
  check('cân bằng đúng thì thưởng sao (2 sao mỗi phương trình mới)', stars() - starsBefore === 2 * eqCount, [starsBefore, stars()]);
  check('nhận huy hiệu Nhà cân bằng và Bậc thầy', progressHas('balancer') && progressHas('master'));
  $('eq-next').click(); await sleep(100);
  check('Phương trình tiếp theo đưa con trỏ vào ô đầu', document.activeElement.id === 'eq-c0' && $('eq-next').hidden);

  /* ---------- Vai 4: giáo viên và nhóm trong lớp ---------- */
  view('lop');
  if (!$('class-box').hidden) {
    $('class-create').click();
    await until(() => $('class-dialog').open);
    const teacher = JSON.parse(sessionStorage.getItem('cv_class_teacher') || 'null');
    check('tạo lớp được mã 6 kí tự', teacher && /^[A-Z2-9]{6}$/.test(teacher.code), teacher);
    check('mã lớp hiện to', $('class-info').textContent.includes(teacher.code));
    $('class-close').click();
    setv('class-code', 'ZZZZZZ'); $('class-join').click(); await until(() => /Không tìm thấy lớp/.test($('class-msg').textContent));
    check('mã lớp sai bị báo', /Không tìm thấy lớp/.test($('class-msg').textContent), $('class-msg').textContent);
    setv('class-code', teacher.code.toLowerCase()); $('class-code').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await until(() => sessionStorage.getItem('cv_class_code') === JSON.stringify(teacher.code));
    check('vào lớp bằng mã viết thường và phím Enter', !$('class-leave').hidden && sessionStorage.getItem('cv_class_code') === JSON.stringify(teacher.code));
    view('them'); setv('group', 'Nhóm E2E');
    view('thuthach');
    [...$('deck-grid').children].find((b) => b.dataset.deck === 'Khởi động').click(); await until(() => visible('mission'));
    $('ch-skip').click(); $('ch-skip').click(); await sleep(200);
    await demo('Nước, sai liên kết'); await demo('Nước, ghép đúng');
    view('lop'); $('class-open').click(); await until(() => $('class-dialog').open);
    const rowsNow = () => [...document.querySelectorAll('#class-table tbody tr')].map((tr) => [...tr.children].map((td) => td.textContent));
    await until(() => rowsNow().length === 1 && rowsNow()[0][3] === '2', 8000);        // bảng tự làm mới mỗi 5 giây
    const row = rowsNow();
    check('bảng điều khiển có nhóm vừa làm', row.length === 1 && row[0][0].startsWith('Nhóm E2E'), row);
    check('bảng ghi tiến độ, lượt, bỏ qua', row[0] && row[0][1].includes('Khởi động') && row[0][3] === '2' && row[0][6] === '2', row[0]);
    $('class-end').click(); await until(() => $('confirm-dialog').open);
    check('kết thúc lớp hỏi xác nhận trong trang', $('confirm-dialog').open);
    $('confirm-no').click(); await sleep(150);
    check('hủy thì giữ lớp', !!sessionStorage.getItem('cv_class_teacher'));
    $('class-end').click(); await until(() => $('confirm-dialog').open); $('confirm-yes').click(); await until(() => !sessionStorage.getItem('cv_class_teacher'));
    check('đồng ý thì xóa lớp', !sessionStorage.getItem('cv_class_teacher') && !$('class-dialog').open);
    const dead = await (await realFetch('/api/classroom', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'join', code: teacher.code }) })).status;
    check('vào lớp đã xóa trả 404', dead === 404, dead);
    check('lớp đã xóa mà học sinh vẫn còn mã lớp trước khi gửi', sessionStorage.getItem('cv_class_code') === JSON.stringify(teacher.code));
    await demo('Nước, ghép đúng');
    await until(() => !sessionStorage.getItem('cv_class_code'));
    check('lớp bị xóa thì học sinh tự ra khỏi lớp và được báo', !sessionStorage.getItem('cv_class_code') && $('class-leave').hidden && /đã kết thúc hoặc hết hạn/.test($('class-msg').textContent), $('class-msg').textContent);
    if (!$('ch-end').disabled) { $('ch-end').click(); await sleep(150); }
  }

  /* ---------- Vai 5: người không có camera, tệp sai ---------- */
  view('ghep');
  const up = async (file) => { const dt = new DataTransfer(); dt.items.add(file); $('file-input').files = dt.files; $('file-input').dispatchEvent(new Event('change')); await sleep(600); };
  await up(new File(['x'], 'a.txt', { type: 'text/plain' }));
  check('tệp không phải ảnh bị từ chối, KIỂM TRA vẫn khóa', /không phải ảnh/.test($('sub').textContent + $('headline').textContent) && $('btn-check').disabled && visible('check-hint'), $('headline').textContent);
  await up(new File(['không phải ảnh thật'], 'g.jpg', { type: 'image/jpeg' }));
  check('ảnh hỏng bị từ chối', /Không đọc được ảnh/.test($('headline').textContent + $('sub').textContent), $('headline').textContent);

  /* ---------- Vai 6: mất mạng, mọi nút backend đều phải báo ---------- */
  let rejections = 0; const onRej = () => rejections++; window.addEventListener('unhandledrejection', onRej);
  window.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
  const offline = /Không kết nối được máy chủ|Mất kết nối/;
  view('them'); $('btn-demo').click(); await until(() => offline.test($('headline').textContent + $('sub').textContent));
  check('mất mạng: Chạy thử có thông báo', offline.test($('headline').textContent + $('sub').textContent), $('headline').textContent);
  view('canbang'); $('eq-check').click(); await until(() => offline.test($('eq-msg').textContent));
  check('mất mạng: Kiểm tra hệ số có thông báo', offline.test($('eq-msg').textContent), $('eq-msg').textContent);
  view('them'); $('btn-report').click(); await until(() => offline.test($('report-text').textContent));
  check('mất mạng: Báo cáo có thông báo', offline.test($('report-text').textContent), $('report-text').textContent); if ($('report-dialog').open) $('btn-close').click();
  window.fetch = realFetch; window.removeEventListener('unhandledrejection', onRej);
  check('mất mạng: không có lỗi bị nuốt', rejections === 0, rejections);

  /* ---------- Vai 7: lưu lựa chọn, điều hướng, bố cục, truy cập ---------- */
  setv('group', 'Nhóm Mây');
  const prefs = JSON.parse(localStorage.getItem('cv_prefs') || '{}');
  check('lưu tên nhóm', prefs.group === 'Nhóm Mây', prefs);
  location.hash = '#/lop'; await until(() => visible('view-lop'));
  check('đường dẫn #/lop mở thẻ Lớp học', visible('view-lop') && $('tab-lop').getAttribute('aria-current') === 'page');
  view('ghep');
  check('mỗi lúc chỉ một thẻ hiển thị', ['ghep', 'thuthach', 'canbang', 'lop', 'them'].filter((v) => visible('view-' + v)).length === 1);
  for (const v of ['ghep', 'thuthach', 'canbang', 'lop', 'them']) {
    view(v); await sleep(80);
    const cw = document.documentElement.clientWidth;      // đo lại mỗi thẻ vì thanh cuộn dọc chỉ xuất hiện ở thẻ dài
    if (cw >= 200) check('thẻ ' + v + ' không tràn ngang', document.documentElement.scrollWidth <= cw + 1, [document.documentElement.scrollWidth, cw]);
    const small = [...document.querySelectorAll('#view-' + v + ' button, #view-' + v + ' select, #view-' + v + ' input:not([type=file]):not([type=checkbox]), .tab')]
      .filter((e) => cw >= 200 && !e.closest('[hidden]') && e.getBoundingClientRect().width > 0 && e.getBoundingClientRect().height < 40).map((e) => e.id || e.textContent.trim().slice(0, 12));
    check('thẻ ' + v + ': nút đủ cao để chạm (>= 40 px)', small.length === 0, small);
  }
  const unnamed = [...document.querySelectorAll('button, select, input')].filter((e) => !(e.getAttribute('aria-label') || (e.labels && e.labels.length) || e.textContent.trim() || e.placeholder) && e.type !== 'file').map((e) => e.id);
  check('mọi điều khiển có tên truy cập', unnamed.length === 0, unnamed);
  check('mỗi thẻ ngoài Ghép thẻ có tiêu đề h1', ['thuthach', 'canbang', 'lop', 'them'].every((v) => $('view-' + v).querySelector('h1')));
  check('không vi phạm chính sách bảo mật (CSP)', csp.length === 0, csp);
  return { passed, failed };

  function progressHas(id) { return window.__cv.progress.load().badges.includes(id); }
};
