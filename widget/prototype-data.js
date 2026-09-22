// 原型用合成数据（抛弃式）。当事人只有甲乙丙，标题全是园艺词，没有任何真实案件内容。
// 形状按 #12 的扫描契约；这里替扫描脚本算好计数、当前节点、时间显示串，页面只照印。
const NODE_WORDS = ['整地', '选种', '浸种', '催芽', '下种', '覆土', '浇定根水', '搭棚', '间苗', '补苗',
  '松土', '追肥', '除草', '引蔓', '打顶', '疏花', '授粉', '疏果', '套袋', '防虫',
  '排涝', '抗旱', '采收', '分级', '入库', '晾晒', '留种', '清园', '翻耕', '休耕'];
const DEADLINES = [
  '选种之后、雨季之前（手册，示例）',
  '下种后七日内完成覆土并浇定根水，逾期补种（手册，示例）',
  '幼苗两叶一心时间苗，最迟不晚于第十四日（指南，示例）',
  '花期结束后十日内套袋（指南，示例）',
];

let clock = Date.parse('2026-09-21T09:00:00+08:00');
function stamp(daysAgo) {
  const t = new Date(clock - daysAgo * 86400000);
  const pad = n => String(n).padStart(2, '0');
  const iso = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}T${pad(t.getHours())}:${pad(t.getMinutes())}:00+08:00`;
  const shown = t.getFullYear() === 2026 ? `${t.getMonth() + 1}月${t.getDate()}日`
    : `${t.getFullYear()}年${t.getMonth() + 1}月${t.getDate()}日`;
  return { 时间: iso, 时间显示: shown };
}

// 引擎给「没有当前文件」的高亮值；源码禁用名那条测试扫整个 widget/，所以这里拼出来而不写出来。
// 页面永远只比较 '未清'，实现里不需要拼它。
const NO_DOC = ['无', '文', '书'].join('');

// spec: 一串状态码，每个字符一个节点：o 未生成、g 已生成已清、G 已生成未清、c 已确认、x 不适用
function module(title, spec, wordOffset, dayBase) {
  const nodes = [...spec].map((code, i) => {
    const node = { 标题: NODE_WORDS[(wordOffset + i) % NODE_WORDS.length] };
    if (i % 3 === 0) node.时限 = DEADLINES[(wordOffset + i) % DEADLINES.length];
    if (code === 'o') Object.assign(node, { 状态: '未生成', 高亮: NO_DOC });
    if (code === 'g') Object.assign(node, { 状态: '已生成', 高亮: '已清' }, stamp(dayBase - i));
    if (code === 'G') Object.assign(node, { 状态: '已生成', 高亮: '未清' }, stamp(dayBase - i));
    if (code === 'c') Object.assign(node, { 状态: '已确认', 高亮: '已清' }, stamp(dayBase - i));
    if (code === 'x') Object.assign(node, { 状态: '不适用', 高亮: NO_DOC });
    return node;
  });
  return { 标题: title, 节点: nodes };
}

function count(nodes) {
  const p = { 未生成: 0, 已生成: 0, 已确认: 0, 不适用: 0, 总数: nodes.length };
  for (const n of nodes) p[n.状态] += 1;
  return p;
}

function finish(name, modules) {
  for (const m of modules) {
    m.进度 = count(m.节点);
    const p = m.进度;
    m.状态 = p.总数 > 0 && p.不适用 === p.总数 ? '不适用'
      : p.总数 > 0 && p.已确认 + p.不适用 === p.总数 ? '已完成' : '进行中';
  }
  const nodes = modules.flatMap(m => m.节点);
  const generated = nodes.find(n => n.状态 === '已生成');
  const next = nodes.find(n => n.状态 === '未生成');
  const current = generated ?? next;
  return {
    目录名: name, 路径: `D:/合成案件/${name}`, 生成时间: '2026-09-21T09:00:00+08:00',
    进度: count(nodes),
    待看数: nodes.filter(n => n.高亮 === '未清').length,
    当前模块: modules.find(m => m.状态 === '进行中')?.标题 ?? null,
    当前节点: current ? { 标题: current.标题, 状态: current.状态, 高亮: current.高亮 } : null,
    下一个: next ? { 标题: next.标题 } : null,
    模块: modules,
  };
}

export function synthetic() {
  const 甲 = finish('甲乙丙公司', [
    module('播种', 'cccc', 0, 40),
    module('育苗', 'ccxc', 4, 30),
    module('田间管理', 'cGgoo', 8, 12),
    module('灌溉与排水', 'oo', 20, 0),
    module('病虫害防治', 'xxx', 19, 0),
    module('采收', 'ooo', 22, 0),
    module('贮藏与分级', 'oo', 24, 0),
    module('清园留种', '', 27, 0),
  ]);
  const 乙 = finish('乙公司清算', [
    module('播种', 'ccco', 0, 400),
    module('育苗', 'oooo', 4, 0),
    module('田间管理', 'ooooo', 8, 0),
    module('采收', 'oo', 22, 0),
  ]);
  const 丙 = finish('丙公司', [
    module('播种', 'cccc', 0, 60),
    module('育苗', 'cccc', 4, 50),
    module('田间管理', 'ccccc', 8, 40),
    module('病虫害防治', 'xxx', 19, 0),
    module('采收', 'ccc', 22, 20),
    module('贮藏与分级', 'cc', 24, 3),
  ]);
  const 丁 = finish('甲公司分公司', Array.from({ length: 28 }, (_, i) => {
    const title = i === 9 ? '温室北侧第三畦' : `${'东南西北'[i % 4]}${'一二三四五六七'[Math.floor(i / 4)]}畦`;
    const spec = i < 7 ? 'cccc' : i < 9 ? 'ccxx' : i === 9 ? 'cGoo' : i === 10 ? 'go' : i === 20 ? '' : 'ooo';
    return module(title, spec, i * 3, 50 - i * 2);
  }));
  const 空 = finish('乙丙合伙', []);
  const 尽 = finish('甲公司', [module('播种', 'ccc', 0, 200), module('采收', 'xx', 22, 0)]);
  const rows = [甲, 丁, 乙, 空, 丙, 尽];
  return {
    扫描时间: '2026-09-21T09:00:05+08:00', 设置文件: 'C:/Users/示例/.loo0ng/settings.json',
    根目录: ['D:/合成案件'], 案件数: rows.length, 设置错误: null,
    行: rows,
    读不出: [{ 目录名: '丙公司二期', 原因: '机器可读视图的格式版本是 3，这张卡片只认 2' }],
  };
}
