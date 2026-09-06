/* ===================== 后端地址 ===================== */
/* 同源相对路径优先（页面即由后端伺服，换端口/局域网 IP 自动适配）；
   仅当以 file:// 直接打开本地文件时回退到默认地址 */
const API_BASE = (location.protocol === 'file:')
  ? 'http://127.0.0.1:8765/api'
  : '/api';

/* ===================== 图标系统（本地 SVG，无外网资源） ===================== */
/* 厂商图标：白色单色极简徽标（保持与 DeepSeek 一致的风格）。
   统一底圆 + 白色字形；未收录的厂商回退灰色圆点。
   匹配支持子串/别名，便于将来按 Provider.base_url 真正接入多厂商。 */
const PROVIDER_ICONS = {
  /* DeepSeek：官方网站原版鲸鱼标志（deepseek.com 内嵌矢量，白色版） */
  deepseek: `<svg viewBox="0 0 27 22" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M26.5174 3.39471C26.235 3.2567 26.1137 3.52006 25.9487 3.65346C25.8923 3.69659 25.8446 3.75294 25.7969 3.80469C25.3846 4.24516 24.9027 4.53439 24.2737 4.49989C23.3536 4.44814 22.5682 4.73737 21.8735 5.44119C21.7258 4.57349 21.2353 4.0554 20.4889 3.72304C20.0985 3.55054 19.7034 3.37746 19.4297 3.00197C19.2388 2.73459 19.1865 2.43673 19.091 2.14289C19.0301 1.96579 18.9697 1.78466 18.7656 1.75418C18.5442 1.71968 18.4574 1.90541 18.3705 2.06067C18.0232 2.69549 17.8887 3.39471 17.9019 4.10313C17.9324 5.6965 18.6051 6.96556 19.9421 7.86834C20.0939 7.97184 20.133 8.07535 20.0852 8.22658C19.9938 8.53766 19.8857 8.83955 19.7903 9.15063C19.7293 9.34901 19.6384 9.39271 19.4257 9.30588C18.692 8.9994 18.0583 8.54571 17.4982 7.99772C16.5477 7.07827 15.6881 6.06336 14.6162 5.26869C14.3644 5.08296 14.1125 4.91045 13.8521 4.746C12.7584 3.68394 13.9952 2.81164 14.2816 2.70814C14.5812 2.60003 14.3857 2.22857 13.4179 2.23317C12.4502 2.2372 11.5646 2.56151 10.4359 2.99335C10.2708 3.05832 10.0972 3.10547 9.91951 3.14457C8.8954 2.95022 7.83162 2.90709 6.72069 3.03245C4.62877 3.26533 2.95777 4.25436 1.72954 5.94261C0.254043 7.97184 -0.0932678 10.2777 0.33167 12.6824C0.778458 15.2171 2.07225 17.3153 4.06008 18.9558C6.12152 20.6567 8.49577 21.4905 11.2047 21.3306C12.8498 21.2358 14.6812 21.0155 16.7473 19.2669C17.2682 19.5262 17.8151 19.6297 18.7219 19.7074C19.4205 19.7723 20.0933 19.6729 20.6143 19.5648C21.4302 19.3923 21.3739 18.6367 21.0789 18.4981C18.6874 17.3843 19.2124 17.8374 18.7351 17.4706C19.9501 16.033 21.8063 13.4776 22.379 9.99821C22.4353 9.61409 22.5072 9.073 22.4986 8.76192C22.494 8.57216 22.5377 8.49856 22.7545 8.47671C23.3536 8.40771 23.935 8.24383 24.4692 7.94999C26.0188 7.10357 26.6439 5.71318 26.7911 4.04678C26.8129 3.79204 26.7865 3.52869 26.5174 3.39471ZM13.0143 18.3946C10.6964 16.5724 9.5722 15.9726 9.10816 15.9985C8.67402 16.0244 8.75222 16.5212 8.84768 16.8449C8.94773 17.1646 9.07768 17.3849 9.25996 17.6655C9.38589 17.8512 9.47272 18.1272 9.13404 18.3348C8.38766 18.7965 7.08985 18.1796 7.0289 18.1491C5.51833 17.2595 4.25559 16.0853 3.36546 14.4793C2.50581 12.9337 2.0067 11.2753 1.92447 9.50542C1.90262 9.07818 2.02855 8.92695 2.45406 8.84932C3.01413 8.74582 3.59144 8.72397 4.15093 8.80619C6.51656 9.15178 8.53027 10.2092 10.2185 11.8848C11.1822 12.8388 11.9114 13.979 12.6623 15.0929C13.461 16.2757 14.3201 17.4027 15.4144 18.3268C15.8008 18.6505 16.109 18.8966 16.404 19.0783C15.5144 19.1778 14.0297 19.1991 13.0143 18.3958V18.3946ZM14.1252 11.2489C14.1252 11.0591 14.277 10.9079 14.4679 10.9079C14.511 10.9079 14.5501 10.9165 14.5852 10.9292C14.6329 10.9464 14.6766 10.9723 14.7111 11.0114C14.7721 11.0718 14.8066 11.158 14.8066 11.2489C14.8066 11.4386 14.6548 11.5899 14.4639 11.5899C14.273 11.5899 14.1252 11.4386 14.1252 11.2489ZM17.5759 13.0188C17.3545 13.1096 17.1331 13.1873 16.9203 13.1959C16.5903 13.2131 16.2303 13.0791 16.0348 12.9153C15.7312 12.6605 15.5139 12.5179 15.423 12.0734C15.3839 11.8837 15.4057 11.5899 15.4402 11.4214C15.5185 11.0585 15.4316 10.8257 15.1757 10.614C14.9676 10.4415 14.7025 10.3938 14.4115 10.3938C14.3029 10.3938 14.2034 10.3461 14.1292 10.3076C14.0079 10.2472 13.9078 10.096 14.0033 9.91023C14.0338 9.84985 14.1815 9.70322 14.216 9.67734C14.6111 9.45251 15.0665 9.52612 15.488 9.6946C15.8784 9.85445 16.174 10.1477 16.5989 10.5623C17.033 11.0631 17.1112 11.2011 17.3585 11.5772C17.554 11.871 17.7317 12.1729 17.8536 12.5185C17.9272 12.7341 17.8317 12.9107 17.5759 13.0188Z" fill="#fff"/>
  </svg>`,
  /* OpenAI：官方网站原版徽标（三环缠绕花，官方矢量，白色版） */
  openai: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z" fill="#fff"/>
  </svg>`,
  /* Anthropic / Claude：官方网站原版徽标（官方矢量，白色版） */
  anthropic: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.3041 3.541h-3.6718l6.696 16.918H24Zm-10.6082 0L0 20.459h3.7442l1.3693-3.5527h7.0052l1.3693 3.5528h3.7442L10.5363 3.5409Zm-.3712 10.2232 2.2914-5.9456 2.2914 5.9456Z" fill="#fff"/>
  </svg>`,
  /* Google Gemini：官方网站原版四角星（官方矢量，白色版） */
  google: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 2.55t2.55 3.81" fill="#fff"/>
  </svg>`,
  /* xAI / Grok：官方网站原版 X 标志（官方矢量，白色版） */
  xai: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z" fill="#fff"/>
  </svg>`,
  /* Qwen 通义：旋尾"千"形火焰流 */
  qwen: `<svg viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.07)"/>
    <path d="M15.4 6C12.9 7.5 9.7 7.6 6.8 6.4c-.5-.2-.6.6-.1.9 2.3 1.2 4 3 5 5.4.3.7-.6 1.1-1 .5-.8-1.3-2-2.5-3.5-3.4-.3-.2-.8 0-.7.4.3 1.6 1 3 2.2 4 1.6-1 3-1.5 4-1.5 1.2 0 2.1.4 2.7 1.2l.6-1.6c.1-.2.3-.3.5-.3.3.1.5.4.5.7 0 .2-.1.5-.3.6-.2.2.1.4.4.2 1.2-2 1.3-7.2-4.6-6.5z" fill="#fff"/>
  </svg>`,
  /* 智谱 GLM：六边形宝石 */
  zhipu: `<svg viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.07)"/>
    <path d="M12 5.6 18.4 9v6l-6.4 3.4L5.6 15V9L12 5.6zM12 8.2 8.4 10v4L12 16l3.6-2v-4L12 8.2z" fill="#fff"/>
  </svg>`,
  /* 豆包：圆润豆荚（两粒豆） */
  doubao: `<svg viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.07)"/>
    <ellipse cx="12" cy="13.1" rx="5.3" ry="3.9" fill="#fff"/>
    <path d="M8.6 13.6c.4-.8 1.1-1.3 2-1.5 1.7-.3 2.8.4 3.6 1.2-.2-.4-.7-1.1-1.1-1.6 1.8-.1 3.6.3 5 1.4-1.2.3-2.4.5-3.6.5-.3 0-.7 0-1-.1 1.5-.2 3-.6 4.3-1.2-.4-1-1.9-1.6-3.4-1.4.4.5.8 1 1 1.3-1.6-.4-3.4-.1-4.7 1.8z" fill="#d9e6ea"/>
  </svg>`,
  /* Kimi 月之暗面：官方矢量徽标（白色单色版，取自官方品牌 SVG） */
  kimi: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21.846 0a1.923 1.923 0 110 3.846H20.15a.226.226 0 01-.227-.226V1.923C19.923.861 20.784 0 21.846 0z" fill="#fff"/>
    <path d="M11.065 11.199l7.257-7.2c.137-.136.06-.41-.116-.41H14.3a.164.164 0 00-.117.051l-7.82 7.756c-.122.12-.302.013-.302-.179V3.82c0-.127-.083-.23-.185-.23H3.186c-.103 0-.186.103-.186.23V19.77c0 .128.083.23.186.23h2.69c.103 0 .186-.102.186-.23v-3.25c0-.069.025-.135.069-.178l2.424-2.406a.158.158 0 01.205-.023l6.484 4.772a7.677 7.677 0 003.453 1.283c.108.012.2-.095.2-.23v-3.06c0-.117-.07-.212-.164-.227a5.028 5.028 0 01-2.027-.807l-5.613-4.064c-.117-.078-.132-.279-.028-.381z" fill="#fff"/>
  </svg>`,
  /* Mistral：蜂窝六边形（M 镂空） */
  mistral: `<svg viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.07)"/>
    <path d="M12 6.2 18.4 9.2v5.6L12 17.8 5.6 14.8V9.2L12 6.2zm0 2.2-4.4 2 .4 3.4 4 1.9-4 4 4-4 4-4-4-1.9.2-3.4z" fill="#fff"/>
  </svg>`,
  /* Meta：官方网站原版徽标（官方矢量，白色版） */
  meta: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6.915 4.03c-1.968 0-3.683 1.28-4.871 3.113C.704 9.208 0 11.883 0 14.449c0 .706.07 1.369.21 1.973a6.624 6.624 0 0 0 .265.86 5.297 5.297 0 0 0 .371.761c.696 1.159 1.818 1.927 3.593 1.927 1.497 0 2.633-.671 3.965-2.444.76-1.012 1.144-1.626 2.663-4.32l.756-1.339.186-.325c.061.1.121.196.183.3l2.152 3.595c.724 1.21 1.665 2.556 2.47 3.314 1.046.987 1.992 1.22 3.06 1.22 1.075 0 1.876-.355 2.455-.843a3.743 3.743 0 0 0 .81-.973c.542-.939.861-2.127.861-3.745 0-2.72-.681-5.357-2.084-7.45-1.282-1.912-2.957-2.93-4.716-2.93-1.047 0-2.088.467-3.053 1.308-.652.57-1.257 1.29-1.82 2.05-.69-.875-1.335-1.547-1.958-2.056-1.182-.966-2.315-1.303-3.454-1.303zm10.16 2.053c1.147 0 2.188.758 2.992 1.999 1.132 1.748 1.647 4.195 1.647 6.4 0 1.548-.368 2.9-1.839 2.9-.58 0-1.027-.23-1.664-1.004-.496-.601-1.343-1.878-2.832-4.358l-.617-1.028a44.908 44.908 0 0 0-1.255-1.98c.07-.109.141-.224.211-.327 1.12-1.667 2.118-2.602 3.358-2.602zm-10.201.553c1.265 0 2.058.791 2.675 1.446.307.327.737.871 1.234 1.579l-1.02 1.566c-.757 1.163-1.882 3.017-2.837 4.338-1.191 1.649-1.81 1.817-2.486 1.817-.524 0-1.038-.237-1.383-.794-.263-.426-.464-1.13-.464-2.046 0-2.221.63-4.535 1.66-6.088.454-.687.964-1.226 1.533-1.533a2.264 2.264 0 0 1 1.088-.285z" fill="#fff"/>
  </svg>`,
};
/* 匹配：按已收录 key + 通用别名；未命中回退白色圆点。 */
function providerIcon(name){
  const n = (name || '').toLowerCase();
  /* 别名归一：让各厂商常见命名都命中同一徽标 */
  const alias = {
    'openai':'openai','gpt':'openai','chatgpt':'openai',
    'anthropic':'anthropic','claude':'anthropic',
    'google':'google','gemini':'google','deepmind':'google',
    'xai':'xai','grok':'xai','x-ai':'xai',
    'qwen':'qwen','aliyun':'qwen','tongyi':'qwen','dashscope':'qwen','通义':'qwen',
    'zhipu':'zhipu','glm':'zhipu','bigmodel':'zhipu','智谱':'zhipu',
    'doubao':'doubao','bytedance':'doubao','volcengine':'doubao','ark':'doubao','豆包':'doubao',
    'moonshot':'kimi','kimi':'kimi','llama':'meta','meta':'meta','meta-llama':'meta'
  };
  let key = (PROVIDER_ICONS[n] && n) || null;
  if (!key){ for (const k in alias){ if (n.includes(k)){ key = alias[k]; break; } } }
  return key ? PROVIDER_ICONS[key]
    : `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.05)" stroke="rgba(255,255,255,.20)"/><circle cx="12" cy="12" r="4" fill="#fff" opacity=".85"/></svg>`;
}
/* ===================== 前端状态 ===================== */
const state = {
  convs: [],          // 由后端 /api/conversations 提供
  activeConv: null,   // 当前对话 id
  renamingId: null,
};

let providers = [];        // 后端返回的厂商列表
let openStates = {};       // provider_id -> 是否展开
let modelOptions = [];     // 可选模型 {provider_id, model_id, label, short}
let selectedModelKey = null;
let pasteProviderId = null;

const STATUS_COLOR = { '正常': 'green', '缓慢': 'yellow', '异常': 'red', '未连接': 'gray' };

/* ===================== 工具 ===================== */
const $ = id => document.getElementById(id);
let toastTimer = null;
/* —— P3 Toast 统一调度器：单元素、队列 + 去重 + 合并。
   保持 toast(msg) 调用方式、显示样式/时长(2200ms)/位置不变；
   同一文案同时段去重（当前显示或队列中已存在则不重复入队，避免闪烁）；
   多条不同 toast 排队顺序展示（单元素不堆叠、不丢失）。 */
const _toastQueue = [];
let _toastActive = false;
let _toastCurrent = '';
function toast(msg){
  if (msg == null) msg = '';
  msg = String(msg);
  if (_toastActive && msg === _toastCurrent) return;   // 去重：正在显示的相同文案不重启
  if (_toastQueue.indexOf(msg) >= 0) return;           // 合并：同名已在队列不重复入队
  _toastQueue.push(msg);
  if (!_toastActive) _toastNext();
}
function _toastNext(){
  if (!_toastQueue.length){ _toastActive = false; return; }
  _toastActive = true;
  _toastCurrent = _toastQueue.shift();
  const t = $('toast');
  if (!t){ _toastActive = false; return; }
  t.textContent = _toastCurrent;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.classList.remove('show'); _toastNext(); }, 2200);
}

const FETCH_TIMEOUT_MS = 15000; // 后端假死时的兜底超时
const STREAM_IDLE_TIMEOUT_MS = 20000; // 流式超过该时长无任何数据帧即中止（防 UI 永久卡死）

async function apiFetch(path, method = 'GET', body = null){
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), FETCH_TIMEOUT_MS);
  const opts = { method, signal: ctl.signal };
  if (body){ opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(body); }
  let r;
  try{
    r = await fetch(API_BASE + path, opts);
  }catch(e){
    if (e.name === 'AbortError'){
      throw new Error('后端无响应（超时 15 秒），请检查服务是否正常运行');
    }
    throw new Error('无法连接后端服务，请先启动 backend');
  }finally{
    clearTimeout(timer);
  }
  let data = null;
  try{ data = await r.json(); }catch(_){}
  if (!r.ok){
    const d = data && (data.detail || data.message);
    throw new Error(humanizeApiErr(d, r.status));  /* 片7 #3：API 错误人话化，消除裸 API 错误上屏 */
  }
  return data;
}

function fmtToken(n){ return Number(n || 0).toLocaleString('zh-CN'); }
function fmtCtx(n){
  n = Number(n || 0);
  if (n >= 1000000) return (n / 1000000).toFixed(n % 1000000 ? 1 : 0) + 'M';
  if (n >= 1000) return Math.round(n / 1000) + 'K';
  return n || '';
}
function modelKey(o){ return o.provider_id + ':' + o.model_id; }

/* ===================== Markdown 渲染（轻量安全实现） ===================== */
function escHtml(s){
  return String(s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function renderMd(src){
  if (!src) return '';
  let t = escHtml(src);
  const codes = [];
  // 围栏代码块（含未闭合的结尾块）
  t = t.replace(/```([\w-]*)\n?([\s\S]*?)(?:```|$)/g, (_, lang, code) => {
    const i = codes.length;
    codes.push(`<pre class="md-code">
<div class="md-code-bar">
  <span class="md-code-lang">${escHtml(lang || 'code')}</span>
  <span class="md-code-ops">
    <button class="md-code-fold" title="折叠/展开"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="fold-icon"><path d="M12 5v14M19 12l-7 7-7-7"/></svg><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="unfold-icon"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
    <button class="md-code-copy" data-copy title="复制代码"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>
  </span>
</div>
<button class="md-code-expand">展开</button>
<code>${code.replace(/\n+$/,'')}</code></pre>`);
    return `\u0000C${i}\u0000`;
  });
  // 行内代码
  t = t.replace(/`([^`\n]+)`/g, '<code class="md-inline">$1</code>');
  // 标题
  t = t.replace(/^#### (.+)$/gm, '<h4>$1</h4>')
       .replace(/^### (.+)$/gm, '<h3>$1</h3>')
       .replace(/^## (.+)$/gm, '<h3>$1</h3>')
       .replace(/^# (.+)$/gm, '<h2>$1</h2>');
  // 粗体 / 斜体
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
       .replace(/(^|[^*\w])\*([^*\n]+)\*(?=\W|$)/g, '$1<em>$2</em>');
  // 链接
  t = t.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  // 引用
  t = t.replace(/^&gt; ?(.+)$/gm, '<p style="border-left:2px solid var(--gold);padding-left:10px;color:var(--dim)">$1</p>');
  // 逐行组装（列表合并、代码占位还原）
  const out = [];
  let list = null;
  const closeList = () => { if (list){ out.push(`</${list}>`); list = null; } };
  for (const line of t.split('\n')){
    const ul = line.match(/^[-*] (.+)$/), ol = line.match(/^\d+\. (.+)$/);
    if (ul || ol){
      const want = ul ? 'ul' : 'ol';
      if (list !== want){ closeList(); out.push(`<${want}>`); list = want; }
      out.push(`<li>${(ul || ol)[1]}</li>`);
      continue;
    }
    closeList();
    const trim = line.trim();
    if (!trim) continue;
    if (/^<(h2|h3|h4|p style|pre|ul|ol)/.test(trim) || /^\u0000C\d+\u0000$/.test(trim)){
      out.push(trim);
    } else {
      out.push(`<p>${trim}</p>`);
    }
  }
  closeList();
  return out.join('').replace(/\u0000C(\d+)\u0000/g, (_, i) => codes[Number(i)]);
}

/* ===================== 通用确认弹窗（删除等危险操作） ===================== */
let confirmResolver = null;
function showConfirm(msg, title = '确认操作', okText = '确定'){
  return new Promise(resolve => {
    confirmResolver = resolve;
    $('confirmTitle').textContent = title;
    $('confirmMsg').textContent = msg;
    $('confirmOk').textContent = okText;
    $('confirmMask').classList.add('open');
  });
}
function closeConfirm(result){
  $('confirmMask').classList.remove('open');
  if (confirmResolver){ confirmResolver(result); confirmResolver = null; }
}
$('confirmOk').addEventListener('click', () => closeConfirm(true));
$('confirmCancel').addEventListener('click', () => closeConfirm(false));
$('confirmMask').addEventListener('click', e => { if (e.target === $('confirmMask')) closeConfirm(false); });

/* ===================== 左侧：对话列表（纯前端） ===================== */
const PIN_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="17" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>';

async function loadConvs(){
  try{
    const data = await apiFetch('/conversations');
    state.convs = data.conversations || [];
    renderConvs();
  }catch(err){ toast('加载对话列表失败：' + err.message); }
}

function renderConvs(){
  const list = state.convs;
  if (!list.length){
    $('convList').innerHTML = `<div class="empty-search">暂无对话，点"新对话"开始</div>`;
    return;
  }
  $('convList').innerHTML = list.map(c => `
    <div class="conv-item ${c.id === state.activeConv ? 'active' : ''}" data-conv="${c.id}" title="${escHtml(c.title)}">
      <svg class="conv-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="conv-name">${escHtml(c.title)}</span>
      ${c.pinned ? `<span class="conv-pin" title="已置顶">${PIN_SVG}</span>` : ''}
    </div>
  `).join('');
}

/* 网络断开横幅：跟随 navigator.onLine */
const netBanner = $('netBanner');
function syncNetBanner(){
  const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
  netBanner.hidden = !offline;
}
window.addEventListener('online', syncNetBanner);
window.addEventListener('offline', syncNetBanner);

/* 无可用模型：由中部空状态卡片接管（syncChatState 在下文布局模块中定义，声明提升） */
syncNetBanner();

let loadMessagesSeq = 0; // 请求序号守卫：快速切换对话时，旧响应不再渲染
async function loadMessages(convId){
  const seq = ++loadMessagesSeq;
  messagesEl.innerHTML = '<div class="msg-loading">加载中…</div>';
  try{
    const data = await apiFetch(`/conversations/${convId}/messages`);
    if (seq !== loadMessagesSeq) return; // 已被更新的切换请求取代，丢弃本次结果
    const list = data.messages || [];
    messagesEl.innerHTML = ''; // 移除加载占位
    if (!list.length){ showChatHint(); return; }
    list.forEach(m => {
      if (m.role === 'user') addUserMsg(m.content, m.images && m.images.length ? m.images : null, m.id);
      else addAiMsg(m.content, m.model_id || null, m.cost ?? 0, m.latency_ms ?? 0, m.id);
    });
    scrollBottom(messagesEl);
    _scrollState(messagesEl).up = false; // 打开对话默认贴底
    updateRegionDownBtns();
  }catch(err){
    if (seq !== loadMessagesSeq) return;
    toast('加载消息失败：' + err.message);
  }
}

function showChatHint(){
  // 空状态不再显示引导文案：留白让输入框垂直居中（chat--empty 承担）
  messagesEl.innerHTML = '';
  syncAgentComposer();
}

$('convList').addEventListener('click', e => {
  if (sending){ toast('回复生成中，请等待完成后再切换对话'); return; }
  const item = e.target.closest('[data-conv]');
  if (!item) return;
  const id = Number(item.dataset.conv);
  if (id === state.activeConv) return;
  state.activeConv = id;
  renderConvs();
  loadMessages(id);
});

/* ---------- 新建对话 / 新建任务：始终分流 ------------------------------------------------------------------
   聊天模式「+ 新对话」→ 不在点击时立即建对话，只清空视图回空白引导态、保留输入框草稿；
                首次发送消息（conversation_id=null）时才由后端创建并回传 id，侧栏同步置顶。
   Agent 模式「+ 新任务」→ 保持现状：清空回任务引导态，输入框内容保留，发送任务时才创建。 */
$('newChatBtn').addEventListener('click', () => {
  if (appEl.classList.contains('mode-agent')){ startNewAgentTask(); return; }
  if (sending){ toast('回复生成中，请等待完成后再新建对话'); return; }
  // 仅切到"未选对话"的空白引导态：不建记录、不清输入框草稿，等首次发送自动创建
  state.activeConv = null;
  renderConvs();
  messagesEl.innerHTML = '';
  showChatHint();
});

/* 右键菜单：历史对话 / 历史任务共用（ctxKind 区分操作对象） */
let ctxConvId = null;
let ctxTaskId = null;
let ctxKind = 'conv';            // 'conv' | 'task'
let ctxTaskRow = null;           // 右键命中的任务行（title/objective/pinned 回填用）
function closeCtx(){ $('ctxMenu').classList.remove('open'); }

$('convList').addEventListener('contextmenu', e => {
  const item = e.target.closest('[data-conv]');
  if (!item) return;
  e.preventDefault();
  ctxKind = 'conv';
  ctxTaskId = null;
  ctxConvId = Number(item.dataset.conv);
  state.activeConv = ctxConvId;
  renderConvs();
  const conv = state.convs.find(c => c.id === ctxConvId);
  $('pinLabel').textContent = conv.pinned ? '取消置顶' : '置顶';
  const m = $('ctxMenu');
  m.classList.add('open');
  m.style.left = Math.min(e.clientX, window.innerWidth - 170) + 'px';
  m.style.top = Math.min(e.clientY, window.innerHeight - 132) + 'px';
});

/* 历史任务右键：与历史对话同款菜单（重命名 / 置顶 / 删除） */
$('taskList').addEventListener('contextmenu', e => {
  const item = e.target.closest('.task-item[data-task]');
  if (!item) return;
  e.preventDefault();
  ctxKind = 'task';
  ctxConvId = null;
  ctxTaskId = item.dataset.task;
  ctxTaskRow = (A.taskRows || []).find(r => r.taskId === ctxTaskId) || null;
  $('pinLabel').textContent = (ctxTaskRow && ctxTaskRow.pinned) ? '取消置顶' : '置顶';
  const m = $('ctxMenu');
  m.classList.add('open');
  m.style.left = Math.min(e.clientX, window.innerWidth - 170) + 'px';
  m.style.top = Math.min(e.clientY, window.innerHeight - 132) + 'px';
});

$('ctxMenu').addEventListener('click', async e => {
  const item = e.target.closest('[data-ctx]');
  if (!item) return;
  const act = item.dataset.ctx;
  closeCtx();
  /* 历史任务分支：重命名 / 置顶 / 删除 */
  if (ctxKind === 'task'){
    const tid = ctxTaskId;
    const row = ctxTaskRow;
    if (!tid) return;
    if (act === 'rename'){
      state.renamingId = tid;
      state.renamingKind = 'task';
      $('renameInput').value = (row && (row.title || row.objective)) || '';
      $('renameMask').classList.add('open');
      setTimeout(() => { $('renameInput').focus(); $('renameInput').select(); }, 30);
    } else if (act === 'pin'){
      try{
        const body = { pinned: !(row && row.pinned) };
        const r = await apiFetch(`/agent/tasks/${tid}`, 'PUT', body);
        const m = r.task;
        toast(m.pinned ? `已置顶「${m.title || m.objective}」` : `已取消置顶「${m.title || m.objective}」`);
        await loadAgentTasks();
      }catch(err){ toast(err.message); }
    } else if (act === 'delete'){
      const name = (row && (row.title || row.objective)) || '该任务';
      const ok = await showConfirm(`确定删除任务「${name}」吗？该任务的全部记录将一并删除，且无法恢复。`, '删除任务', '删除');
      if (!ok) return;
      deleteAgentTask(tid, null);
    }
    return;
  }
  /* 历史对话分支（原有逻辑） */
  if (ctxConvId === null) return;
  const conv = state.convs.find(c => c.id === ctxConvId);
  if (!conv) return;
  if (act === 'rename'){
    state.renamingId = conv.id;
    state.renamingKind = 'conv';
    $('renameInput').value = conv.title;
    $('renameMask').classList.add('open');
    setTimeout(() => { $('renameInput').focus(); $('renameInput').select(); }, 30);
  } else if (act === 'pin'){
    try{
      await apiFetch(`/conversations/${conv.id}`, 'PUT', { pinned: !conv.pinned });
      toast(!conv.pinned ? `已置顶「${conv.title}」` : `已取消置顶「${conv.title}」`);
      await loadConvs();
    }catch(err){ toast(err.message); }
  } else if (act === 'delete'){
    const ok = await showConfirm(
      `确定删除对话「${conv.title}」吗？该对话的全部消息将一并删除，且无法恢复。`,
      '删除对话', '删除');
    if (!ok) return;
    try{
      await apiFetch(`/conversations/${conv.id}`, 'DELETE');
      toast(`已删除「${conv.title}」`);
      if (state.activeConv === conv.id){
        state.activeConv = null;
        messagesEl.innerHTML = '';
        showChatHint();
      }
      await loadConvs();
      if (state.activeConv === null && state.convs.length){
        state.activeConv = state.convs[0].id;
        renderConvs();
        loadMessages(state.activeConv);
      }
    }catch(err){ toast(err.message); }
  }
});

/* 重命名弹窗 */
function closeRename(){
  $('renameMask').classList.remove('open');
  state.renamingId = null;
}
async function confirmRename(){
  const val = $('renameInput').value.trim();
  const kind = state.renamingKind || 'conv';
  const id = state.renamingId;
  closeRename();
  if (!val) return;
  /* 历史任务重命名：PUT /agent/tasks/{id} {title}（空值在后端回退显示 objective） */
  if (kind === 'task'){
    if (!id) return;
    try{
      await apiFetch(`/agent/tasks/${id}`, 'PUT', { title: val });
      await loadAgentTasks();
    }catch(err){ toast(err.message); }
    return;
  }
  const conv = state.convs.find(c => c.id === id);
  if (conv){
    try{
      await apiFetch(`/conversations/${conv.id}`, 'PUT', { title: val });
      await loadConvs();
    }catch(err){ toast(err.message); }
  }
}
$('renameOk').addEventListener('click', confirmRename);
$('renameCancel').addEventListener('click', closeRename);
$('renameMask').addEventListener('click', e => { if (e.target === $('renameMask')) closeRename(); });
$('renameInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') confirmRename();
  if (e.key === 'Escape') closeRename();
});

/* ===================== 中间：消息 ===================== */
const messagesEl = $('messages');
/* ============ P4 滚动主权：多滚动区共用同一实现（片 1） ============
   聊天流 `.messages`、Agent 中间时间线 `#taskView`、右侧执行面板 `.agent-pane-stream`
   统一走这里的控制器：用户上翻即锁定跟随，回到底部才恢复，绝不因内容增长被拉回。
   开关注册见 window.MONSTERA_CH.agentScroll（片 1 起默认开启）。 */
/** 钉底判定：距底部阈值内视为"贴底"。供所有滚动区共用。 */
function isPinnedToBottom(el, thr = 80){
  return el.scrollHeight - el.scrollTop - el.clientHeight <= thr;
}
const _scrollRegions = new Map();   // 容器 -> { up, btn, thr }
function _scrollState(el){
  if (!_scrollRegions.has(el)){
    _scrollRegions.set(el, { up: false, btn: null, thr: 80 });
  }
  return _scrollRegions.get(el);
}
function scrollBottom(el){
  el.scrollTop = el.scrollHeight;
}
function maybeAutoScroll(el){
  const s = _scrollState(el);
  if (!s.up) scrollBottom(el);
}
/** 某滚动区用户上翻 → 锁定跟随；到达底部或点回底按钮 → 解锁。 */
function bindScrollRegion(el, btnEl, thr = 80){
  const s = _scrollState(el);
  s.btn = btnEl || null; s.thr = thr;
  el.addEventListener('scroll', () => {
    s.up = !isPinnedToBottom(el, thr);
    updateRegionDownBtns();
  });
  if (s.btn){
    s.btn.addEventListener('click', () => {
      scrollBottom(el);
      s.up = false;
      updateRegionDownBtns();
    });
  }
}
/* 回区扫描：每个绑定了按钮的滚动区，按 own up 显隐自己的回底按钮（片 1 泛化，取代单聊天区逻辑） */
function updateRegionDownBtns(){
  _scrollRegions.forEach((s, el) => {
    if (!s.btn) return;
    s.btn.classList.toggle('show', s.up && !isPinnedToBottom(el, 12));
  });
}
/* 回到底部按钮（聊天区实例）。Agent 两区的按钮在 initAgentScrollRegion 内创建。 */
const scrollDownBtn = $('scrollDownBtn');
bindScrollRegion(messagesEl, scrollDownBtn);
/* Agent 区滚动主权（片 1）：中间时间线 + 右侧执行面板共用同一控制器。
   开关注册：观察者/验收可置 window.MONSTERA_CH.agentScroll=false 一键回退片 1。
   两个滚动容器需 overflow-anchor:none（CSS 已加），Safari 不支持故脚本判定自给。 */
window.MONSTERA_CH = window.MONSTERA_CH || {};
window.MONSTERA_CH.agentScroll = true;
window.MONSTERA_CH.foldPersist = true;   // 片 2：过程 chip 展开态保活（活过 SSE 帧重建）
window.MONSTERA_CH.evidenceBlocks = false; // 片 8：C3 证物袋（默认休眠，验收通过前不切默认）
window.MONSTERA_CH.mutualLocate   = false; // 片 8：I1/I2 互定位（默认休眠，验收通过前不切默认）
/* 用户手动展开的过程步骤序号集合（P1 dataset 模式：stepNo 为稳定键，帧间不变）。
   agentViewRender 重建前捕获 .fmsg-chip.open 的 stepNo 写入；重建后 fmsgChipHtml 据此恢复。
   live 步强制展开，不写入集合；已结束步才参与持久化。 */
const fmsgOpenSteps = new Set();   // Set<number stepNo>
let fmsgOpenForTaskId = null;      // 片 2：展开集合归属的任务 id（切换任务即清，防 stepNo 串号）
/* 片 1 P4：Agent 区回底按钮 + 滚动绑定（渲染后调用，每次 ensure）：
   - #taskView 节点稳定，仅首次绑定；按钮每次渲染后重挂（内容重建会抹掉它）。
   - .agent-pane-stream 由 agentPaneRender 整体重建（新节点）→ 每次 ensure 重新 bind。
   - ensure 幂等：已绑定的容器只更新按钮，不重复挂滚动监听。 */
function ensureAgentScrollRegion(el){
  if (!window.MONSTERA_CH || window.MONSTERA_CH.agentScroll === false) return;
  if (!el) return;
  el.querySelector('.scroll-down-agent')?.remove();
  const b = document.createElement('button');
  b.className = 'scroll-down-agent';
  b.title = '回到底部'; b.setAttribute('aria-label', '回到底部');
  b.textContent = '回到底部';
  el.appendChild(b);
  if (_scrollRegions.has(el)){
    const s = _scrollRegions.get(el);
    s.btn = b;
    b.addEventListener('click', () => { scrollBottom(el); s.up = false; updateRegionDownBtns(); });
  } else {
    bindScrollRegion(el, b, 80);
  }
  updateRegionDownBtns();
}

function addUserMsg(text, images, msgId){
  const div = document.createElement('div');
  div.className = 'msg-user msg-in';
  if (images && images.length){
    // 用户附图：缩略图显示在文本上方；已随消息一并落库，历史重开仍显示
    div.appendChild(renderUserImages(images));
    if (text) div.appendChild(document.createTextNode('\n' + text));
  } else {
    div.textContent = text || '';
  }
  // 已落库的历史消息：记录消息 id，供右键菜单定位操作
  if (msgId){
    div.dataset.msgId = msgId;
    mountMsgOps(div, 'user');   // hover 操作条：编辑 / 删除
  }
  messagesEl.appendChild(div);
  scrollBottom(messagesEl);
  _scrollState(messagesEl).up = false; // 新内容入视口：回到贴底状态，后续流式才能自动跟进
  return div; // 失败时据此移除未落库的"幽灵"气泡，保持 UI 与后端一致
}
function renderUserImages(images){
  const wrap = document.createElement('span');
  wrap.className = 'user-imgs';
  images.forEach(url => {
    const img = document.createElement('img');
    img.src = url; img.alt = '';
    wrap.appendChild(img);
  });
  return wrap;
}
/* 流式渲染节流：delta 帧先累积，requestAnimationFrame 每帧至多全量重渲一次
   （原来每个 delta 都 renderMd，长回复 O(n²) 卡顿） */
let streamRafPending = false;
function streamRender(bubble, text){
  bubble._acc = text;
  if (streamRafPending) return;
  streamRafPending = true;
  requestAnimationFrame(() => {
    streamRafPending = false;
    bubble.innerHTML = renderMd(bubble._acc || '');
    maybeAutoScroll(messagesEl); // 仅在贴底时跟进，用户上翻时保持其阅读位置
  });
}
function setAiContent(bubble, text){
  bubble.innerHTML = renderMd(text);
  enhanceCodeBlocks(bubble);
  enhanceLongReplies(bubble);
  maybeAutoScroll(messagesEl);
}

/* —— Phase 6 交互：AI 超长回复默认折叠 + 「展开全文/收起」
   只折叠真正超高的内容；bubble 元素层级通过 dataset 防重复处理（流式重建不闪、不改动用户展开状态） */
function enhanceLongReplies(bubble){
  if (!bubble || bubble.classList.contains('msg-user')) return;
  if (bubble.dataset.aiFold !== undefined) return;   // 已初始化：保留用户当前折叠/展开状态
  if (bubble.scrollHeight <= 540) return;            // 内容不高，无需折叠
  bubble.classList.add('ai-fold');
  const btn = document.createElement('button');
  btn.className = 'ai-fold-btn';
  btn.textContent = '展开全文';
  btn.addEventListener('click', () => {
    const folded = bubble.classList.toggle('ai-fold');
    btn.textContent = folded ? '展开全文' : '收起';
  });
  bubble.after(btn);
  bubble.dataset.aiFold = '1';
}

/* 代码块增强：检测长代码默认收折（仅当实际超阈值），并给折叠/展开按钮赋值 */
function enhanceCodeBlocks(container){
  container.querySelectorAll('pre.md-code').forEach(pre => {
    const code = pre.querySelector('code');
    const fold = pre.querySelector('.md-code-fold');
    const expand = pre.querySelector('.md-code-expand');
    if (!code || !fold) return;
    // 默认折叠状态：内容足够长（按行数粗判）才收起，短代码保持完全展开
    const tall = (code.textContent.split('\n').length) >= 14 || code.scrollHeight > 300;
    pre.classList.toggle('collapsed', tall);
    expand.style.display = tall ? '' : 'none';
    /* 折叠/展开 单钮切换 */
    if (pre.dataset.foldBound) return;
    pre.dataset.foldBound = '1';
    pre.addEventListener('click', e => {
      const f = e.target.closest('.md-code-fold');
      const ex = e.target.closest('.md-code-expand');
      if (f){
        e.stopPropagation();
        pre.classList.toggle('collapsed');
        expand.style.display = pre.classList.contains('collapsed') ? '' : 'none';
      } else if (ex){
        e.stopPropagation();
        pre.classList.remove('collapsed');
        expand.style.display = 'none';
      }
    });
  });
}
function buildMsgMeta(wrap, label, cost, latencyMs, rawText){
  wrap._text = rawText != null ? rawText : (wrap._text || '');
  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  const metaText = document.createElement('span');
  metaText.className = 'meta-text';
  if (label === null){
    metaText.textContent = '已停止';
  } else {
    // Phase 6 UI 极简：只显示模型名，费用/耗时移到悬停提示（减少每条消息的视觉噪声）
    metaText.textContent = label;
    const cs = [];
    if (cost != null) cs.push(`费用 ¥${cost}`);
    if (latencyMs != null) cs.push(`${(latencyMs / 1000).toFixed(1)}s`);
    if (cs.length) metaText.title = '模型 ' + label + ' · ' + cs.join(' · ');
  }
  meta.append(metaText);
  return meta;
}
function addAiMsg(text, label, cost, latencyMs, msgId){
  const wrap = document.createElement('div');
  wrap.className = 'msg-ai-wrap msg-in';
  if (msgId) wrap.dataset.msgId = msgId;
  const bubble = document.createElement('div');
  bubble.className = 'msg-ai';
  wrap.appendChild(bubble);
  if (label !== null){
    wrap.appendChild(buildMsgMeta(wrap, label, cost, latencyMs, text));
  }
  setAiContent(bubble, text);
  if (msgId) mountMsgOps(wrap, 'ai');   // hover 操作条：复制 / 重新生成 / 删除
  messagesEl.appendChild(wrap);
  scrollBottom(messagesEl);
  return wrap;
}

// 空状态提示（点击历史对话后由 loadMessages 接管渲染）
showChatHint();

/* ===================== 输入区 ===================== */
const inputEl = $('input');
function autoResize(){
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}
inputEl.addEventListener('input', () => {
  autoResize();
  updateSendState();
  if (sending) inputDirtyDuringSend = true;
});

function currentModelOption(){
  return modelOptions.find(o => modelKey(o) === selectedModelKey) || null;
}

let attachedImages = []; // 待发送图片（压缩后的 dataURL），随下一条消息一并发出
let sending = false;
let inputDirtyDuringSend = false; // 发送期间用户是否已改动输入框（决定失败时是否找回原文）
let sendAbort = null;            // 当前流式请求的终止控制器（供"停止生成"使用）
let stopRequested = false;       // 用户主动停止（区别于超时/异常）
let lastTurn = null;             // 最近一次成功发出的用户回合（重新生成用）
function updateSendState(){
  const busy = sending;
  $('sendBtn').disabled = busy || (!attachedImages.length && !inputEl.value.trim());
  // 字符计数（DeepSeek 式）：输入达到一定量后显示，逼近上限变色
  const cc = $('charCount');
  const n = inputEl.value.length;
  if (n >= 2000){
    cc.hidden = false;
    cc.textContent = `${n} / 6000`;
    cc.className = 'char-count' + (n >= 5950 ? ' danger' : n >= 5600 ? ' warn' : '');
  } else {
    cc.hidden = true;
  }
}
async function sendMessage(payload){
  // Phase 4：Agent 模式下，底部输入即任务目标，走独立的任务执行链路
  if (appEl.classList.contains('mode-agent')){
    const text = payload ? payload.text : inputEl.value.trim();
    if (!text || A.running) return;
    if (!payload) inputEl.value = '';
    autoResize();
    return startAgentTask(text);
  }
  // payload 用于"失败重试"：显式指定待发送的文本与图片；否则从输入框/待发图读取
  const text = payload ? payload.text : inputEl.value.trim();
  const images = payload ? payload.images : attachedImages.map(im => im.dataUrl);
  const hasImg = images.length > 0; // 支持只发图片（不带文字）
  if ((!text && !hasImg) || sending) return;
  const opt = currentModelOption();
  if (!opt){ toast('暂无可用模型，请先在右侧粘贴 API Key'); return; }
  if (hasImg && !opt.vision){ toast('当前模型不支持图片，请更换支持视觉的模型'); return; }
  sending = true;
  inputDirtyDuringSend = false;
  stopRequested = false;
  $('sendBtn').style.display = 'none';
  $('stopBtn').style.display = 'flex';
  $('genHint').hidden = false;
  const userBubble = addUserMsg(text, images);
  if (!payload) inputEl.value = ''; // 重试时不触碰输入框已有内容
  autoResize();
  const hint = messagesEl.querySelector('.chat-hint');
  if (hint) hint.remove();
  const wrap = addAiMsg('', null);
  const bubble = wrap.querySelector('.msg-ai');
  bubble.innerHTML = '<span class="tdot"></span><span class="tdot"></span><span class="tdot"></span>';
  bubble.classList.add('thinking');
  let fail = msg => {
    wrap.remove();
    if (!inputDirtyDuringSend) inputEl.value = text; // 未改动才找回原文；已改动则保留用户新输入
    autoResize();
    // 消息未落库：保留用户气泡，下方追加"发送失败 + 重试"一键重发，无需重新输入
    showFailRetry(userBubble, text, images, msg);
  };
  try{
    // 流式接口：逐块渲染（SSE）；失败/中断时后端不落库任何消息，前端同步移除气泡
    const ctl = new AbortController();
    sendAbort = ctl;
    let lastFrameAt = Date.now();
    const idleTimer = setInterval(() => {
      if (Date.now() - lastFrameAt > STREAM_IDLE_TIMEOUT_MS) ctl.abort();
    }, 1000);
    try{
      const resp = await fetch(API_BASE + '/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        signal: ctl.signal,
        body: JSON.stringify({
          provider_id: opt.provider_id,
          model_id: opt.model_id,
          message: text,
          images: images, // 多模态：随消息附带图片（无图时为空数组；重试沿用原图）
          conversation_id: state.activeConv,
        }),
      });
      if (!resp.ok){
        let data = null; try{ data = await resp.json(); }catch(_){}
        const d = data && (data.detail || data.message);
        fail(typeof d === 'string' ? d : `请求失败（${resp.status}）`);
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '', acc = '', meta = null, streamErr = null;
      const handleFrame = payload => {
        lastFrameAt = Date.now(); // 收到任意帧即刷新空闲计时
        if (payload === '[DONE]') return;
        let evt; try{ evt = JSON.parse(payload); }catch(_){ return; }
        if (evt.type === 'delta'){
          if (acc === ''){ bubble.replaceChildren(); bubble.classList.remove('thinking'); } // 清掉思考圆点
          acc += evt.content;
          streamRender(bubble, acc); // rAF 节流渲染
          bubble.classList.add('cursor-blink');
        } else if (evt.type === 'meta'){
          meta = evt;
        } else if (evt.type === 'error'){
          streamErr = evt.error;
        }
      };
      while (true){
        const {done, value} = await reader.read();
        if (done) break;
        buf += decoder.decode(value, {stream: true});
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0){
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          if (frame.startsWith('data:')) handleFrame(frame.slice(5).trim());
        }
      }
      bubble.classList.remove('cursor-blink');
      if (streamErr){ fail(streamErr); return; }
      if (!meta){ fail('连接中断，请重试'); return; }
      setAiContent(bubble, acc); // 收尾：确保最终全文渲染（覆盖节流残帧）
      if (!state.activeConv) state.activeConv = meta.conversation_id;
      wrap.appendChild(buildMsgMeta(wrap, opt.label, meta.price_known === false ? null : meta.cost, meta.latency_ms, acc));
      // 回填落库 id：流式收尾才落库，故在此才取得真实 message id。
      // 赋予后用户消息/AI 回复均可用操作条与右键菜单进行编辑/删除。
      if (meta.user_message_id){ userBubble.dataset.msgId = meta.user_message_id; mountMsgOps(userBubble, 'user'); }
      if (meta.assistant_message_id){ wrap.dataset.msgId = meta.assistant_message_id; mountMsgOps(wrap, 'ai'); }
      // 局部更新：对话列表只动当前条目（标题/排序），厂商卡片仅数据变化时重渲，避免闪烁
      updateConvLocal(meta.conversation_id, { title: meta.title, updated_at: new Date().toISOString() });
      loadProviders();
      lastTurn = { text, images: attachedImages.slice() }; // 记录回合，供"重新生成"
      clearAttachments(); // 发送成功：清空待发图片（失败时保留以便重发）
    }catch(err){
      if (err && err.name === 'AbortError'){
        if (stopRequested){
          // 用户主动"停止生成"：保留已输出的部分内容（不落库，本次会话可见）
          bubble.replaceChildren(); bubble.classList.remove('thinking','cursor-blink');
          setAiContent(bubble, acc);
          wrap.appendChild(buildMsgMeta(wrap, null, null, 0, acc));
          lastTurn = { text, images: attachedImages.slice() };
          clearAttachments();
          toast('已停止生成，保留当前内容');
        } else {
          fail('后端流式响应超时，请检查服务后重试');
        }
      } else {
        fail(err.message);
      }
    }finally{
      clearInterval(idleTimer);
    }
  }catch(err){
    fail(err.message);
  }finally{
    sending = false;
    sendAbort = null;
    $('stopBtn').style.display = 'none';
    $('sendBtn').style.display = 'flex';
    $('genHint').hidden = true;
    updateSendState();
  }
}
/* 失败重试：保留用户气泡，在下方追加内联失败提示 + 重试按钮（一键重发，无需重新输入） */
function showFailRetry(userBubble, text, images, msg){
  if (!userBubble) return;
  const tag = document.createElement('div');
  tag.className = 'msg-fail-tag';
  const label = document.createElement('span');
  label.textContent = '发送失败：' + msg;
  const retry = document.createElement('button');
  retry.className = 'msg-retry-btn';
  retry.textContent = '重试';
  retry.addEventListener('click', () => {
    tag.remove();
    userBubble.remove();
    sendMessage({ text, images });
  });
  tag.append(label, retry);
  userBubble.after(tag);
}
/* ===== 图片上传：选图→预览（可删）→原图随消息发送 ===== */
const IMG_MAX = 4;        // 单条消息最多附带图片数
const IMG_MAX_BYTES = 10 * 1024 * 1024; // 单张图片硬上限，超过直接提示（不静默压缩到不可用）
const IMG_MAX_EDGE_HD = 2048; // 高清阈值：长边超过才压（分辨率足够不糊）
const IMG_REENCODE_BYTES = 4 * 1024 * 1024; // 原始字节阈值：哪怕分辨率小，字节过大也强制重编码减体积（保持原分辨率）
const IMG_JPEG_QUALITY = 0.85; // JPEG 有损压缩质量（截图/文字场景保持清晰）

function pickImages(){ $('imageInput').click(); }
function clearAttachments(){ attachedImages.length = 0; renderAttachments(); updateSendState(); }
function renderAttachments(){
  const row = $('attachRow');
  if (!attachedImages.length){ row.innerHTML = ''; row.classList.remove('show'); return; }
  row.classList.add('show');
  row.innerHTML = attachedImages.map((im, i) => `
    <span class="attach-item">
      <img src="${im.dataUrl}" alt="">
      <button class="attach-del" data-i="${i}" title="移除">×</button>
    </span>
  `).join('');
}
$('attachRow').addEventListener('click', e => {
  const del = e.target.closest('.attach-del');
  if (!del) return;
  attachedImages.splice(Number(del.dataset.i), 1);
  renderAttachments();
  updateSendState();
});
$('imageInput').addEventListener('change', async e => {
  const files = Array.from(e.target.files || []);
  e.target.value = '';
  if (!files.length) return;
  let added = 0;
  for (const f of files){
    if (attachedImages.length >= IMG_MAX){ toast(`最多附加 ${IMG_MAX} 张图片`); break; }
    try {
      const dataUrl = await fileToDataURL(f);
      attachedImages.push({ dataUrl, name: f.name || 'image' });
      renderAttachments();
      added++;
    } catch (err){
      toast('图片读取失败：' + (err && err.message ? err.message : err));
    }
  }
  if (added) updateSendState();
});
function fileToDataURL(file){
  return new Promise((resolve, reject) => {
    // 图片策略（对齐主流平台，兼顾“清晰”与“体积”）：
    //   1) 长边超 2048 → 等比降分辨率到 2048（高清不糊）；
    //   2) 即便分辨率偏小，只要原始字节 > IMG_REENCODE_BYTES → 也重编码一次削体积（不降分辨率）；
    //   3) 分辨率小且字节小 → 原样直传，零损耗。
    if (file.size > IMG_MAX_BYTES){
      reject(new Error(`图片 ${file.name || ''} 过大（超过 ${(IMG_MAX_BYTES / 1048576).toFixed(0)}MB），请压缩后重传`));
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('读取失败'));
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const { width: w, height: h } = img;
        const needDownscale = Math.max(w, h) > IMG_MAX_EDGE_HD;      // 分辨率过大
        const needReencode = needDownscale || file.size > IMG_REENCODE_BYTES; // 或字节过大
        if (!needReencode){
          // 分辨率与字节都小 → 原样直传（不缩放、不重编码）
          const url = reader.result;
          if (typeof url !== 'string' || !/^data:image\//.test(url)){
            reject(new Error('不是有效的图片文件')); return;
          }
          resolve(url);
          return;
        }
        // 重编码（需要降分辨率时才缩放，否则保持原尺寸）
        const scale = needDownscale ? IMG_MAX_EDGE_HD / Math.max(w, h) : 1;
        const cw = needDownscale ? Math.max(1, Math.round(w * scale)) : w;
        const ch = needDownscale ? Math.max(1, Math.round(h * scale)) : h;
        const canvas = document.createElement('canvas');
        canvas.width = cw; canvas.height = ch;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, cw, ch);
        // 检测真实透明度：PNG 里绝大多数是不透明照片，转 JPEG 才能大幅瘦身；
        // 仅当确实存在透明像素时才保留 PNG（防透明区变黑底）。
        let hasAlpha = true;
        try {
          const data = ctx.getImageData(0, 0, cw, ch).data;
          hasAlpha = false;
          for (let i = 3; i < data.length; i += 4){
            if (data[i] < 250){ hasAlpha = true; break; }
          }
        } catch (_){ hasAlpha = true; }
        const mime = hasAlpha ? 'image/png' : 'image/jpeg'; // 有透明像素→PNG；否则 JPEG（最省体积）
        const quality = mime === 'image/jpeg' ? IMG_JPEG_QUALITY : undefined;
        canvas.toBlob(blob => {
          if (!blob){ reject(new Error('图片编码失败')); return; }
          // 极少数情况下（如原 PNG 已高度压缩）编码后仍偏大：降质再试一次，保证体积确实变小
          const fr = new FileReader();
          fr.onerror = () => reject(new Error('编码失败'));
          fr.onload = () => {
            const url = fr.result;
            if (typeof url === 'string' && mime === 'image/jpeg' && url.length > file.size * 1.3 + 2048){
              // 兜底：JPEG 重编码没变小则再用更低质量重试（正常不会走到）
              canvas.toBlob(b2 => {
                if (!b2){ reject(new Error('图片编码失败')); return; }
                const fr2 = new FileReader();
                fr2.onerror = () => reject(new Error('编码失败'));
                fr2.onload = () => resolve(fr2.result);
                fr2.readAsDataURL(b2);
              }, 'image/jpeg', 0.6);
              return;
            }
            resolve(url);
          };
          fr.readAsDataURL(blob);
        }, mime, quality);
      };
      img.onerror = () => reject(new Error('不是有效的图片文件'));
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}
/* B5：发送成功后的对话列表局部更新 —— 不再全量 loadConvs() */
function updateConvLocal(convId, patch){
  let conv = state.convs.find(c => c.id === convId);
  if (!conv){
    conv = { id: convId, title: patch.title || '新对话', pinned: false, updated_at: patch.updated_at };
    state.convs.push(conv);
  } else {
    Object.assign(conv, patch);
  }
  state.convs.sort((a, b) =>
    (b.pinned - a.pinned) ||
    (new Date(b.updated_at || 0) - new Date(a.updated_at || 0)));
  renderConvs();
}
// 注意：必须用箭头函数包裹，直接传 sendMessage 会把 MouseEvent 当成 payload 传入，
// 导致 payload.text 为 undefined、消息被 (!text && !hasImg) 判断直接 return，发不出消息。
$('sendBtn').addEventListener('click', () => sendMessage());
/* "停止生成/停止任务"：Agent 执行期间按钮切换为停止任务（与聊天模式交互一致） */
$('stopBtn').addEventListener('click', () => {
  if (appEl.classList.contains('mode-agent') && A && A.running && A.activeTaskId){
    apiFetch(`/agent/tasks/${A.activeTaskId}/stop`, 'POST').then(
      () => toast('已发送停止指令'),
      () => toast('停止失败，请稍后再试'));
    return;
  }
  if (!sending || !sendAbort) return;
  stopRequested = true;
  sendAbort.abort();
});
inputEl.addEventListener('keydown', e => {
  // Enter 发送；Shift+Enter 换行；中文输入法选词期间的 Enter 不应触发发送
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229){
    e.preventDefault();
    sendMessage();
  }
});

/* 消息操作事件委托：hover 操作条 / 展开详情复制 / 代码块复制
   （右键菜单的复制/重新生成/编辑/删除仍走 msgCtx，Handler 相同） */
messagesEl.addEventListener('click', e => {
  /* hover 操作条（Codex 语义）：复制 / 重新生成 / 编辑 / 删除 */
  const op = e.target.closest('[data-msg-act]');
  if (op){
    e.stopPropagation();
    const el = op.closest('.msg-ai-wrap, .msg-user');
    if (!el || !el.dataset.msgId) return;
    const act = op.dataset.msgAct;
    if (act === 'copy'){
      const text = el._text || el.textContent;
      if (text && text.trim()) navigator.clipboard.writeText(text.trim()).then(() => toast('已复制'), () => toast('复制失败'));
      else toast('暂无可复制的内容');
    } else if (act === 'edit'){ handleMsgEdit(el, Number(el.dataset.msgId)); }
    else if (act === 'regen'){ regenTurn(el); }
    else if (act === 'del'){ handleMsgDelete(el, Number(el.dataset.msgId)); }
    return;
  }
  /* 展开详情「复制」ghost 按钮（Codex copy-output 语义）：
     只复制该详情块的数据部分，不含「— 标签 —」与按钮本身 */
  const cex = e.target.closest('[data-copy-extra]');
  if (cex){
    e.stopPropagation();
    const head = cex.closest('.extra-head');
    const box = head && head.parentElement;
    if (!box) return;
    const clone = box.cloneNode(true);
    const h = clone.querySelector('.extra-head');
    if (h) h.remove();
    const text = (clone.textContent || '').trim();
    navigator.clipboard.writeText(text)
      .then(() => { toast('已复制'); }, () => toast('复制失败，请手动复制'));
    return;
  }
  /* 代码块复制 */
  const cpy = e.target.closest('[data-copy]');
  if (cpy){
    const pre = cpy.closest('pre.md-code');
    const code = pre && pre.querySelector('code');
    navigator.clipboard.writeText(code ? code.textContent : '').then(
      () => { cpy.classList.add('copied'); cpy.title = '已复制';
        setTimeout(() => { cpy.classList.remove('copied'); cpy.title = '复制代码'; }, 1400); },
      () => toast('复制失败，请手动复制'));
    return;
  }
});
/* 消息右键菜单：右击任一条已落库消息弹出上下文菜单（复制/重新生成/删除；用户消息为编辑/删除）
   替代旧版"右键即删除"——现在右键只是弹出菜单，具体操作需用户选择，杜绝误删 */
let ctxMsgEl = null;           // 被右键的目标消息元素
const msgCtx = $('msgCtxMenu'); // 右键菜单容器

function closeMsgCtx(){ msgCtx.classList.remove('open'); ctxMsgEl = null; }

/* 消息右键菜单项模板：仅图标 + 文字，点击后由 msgCtx 委托分发 */
const _MCTX_ICON = {
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
  regen: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>',
  del: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>',
};

/* 消息 hover 操作条（Codex 语义）：常态不可见，hover 消息时浮现 icon 组 */
function mountMsgOps(el, kind){
  if (!el || el.querySelector('.msg-ops')) return;
  const acts = kind === 'user' ? ['edit', 'del'] : ['copy', 'regen', 'del'];
  const titleMap = { copy: '复制', regen: '重新生成', edit: '编辑', del: '删除' };
  const ops = document.createElement('span');
  ops.className = 'msg-ops';
  ops.innerHTML = acts.map(a =>
    `<button class="msg-op" data-msg-act="${a}" title="${titleMap[a]}">${_MCTX_ICON[a]}</button>`).join('');
  el.appendChild(ops);
}
function openMsgCtx(x, y, target){
  const isUser = target.classList.contains('msg-user');
  const id = Number(target.dataset.msgId);
  if (!id) return;
  ctxMsgEl = target;
  const item = (act, label, danger) =>
    `<div class="ctx-item${danger ? ' danger' : ''}" data-mact="${act}">${_MCTX_ICON[act]}${label}</div>`;
  msgCtx.innerHTML = isUser
    ? item('edit', '编辑') + item('del', '删除', true)
    : item('copy', '复制回复') + item('regen', '重新生成') + item('del', '删除', true);
  msgCtx.classList.add('open');
  msgCtx.style.left = Math.min(x, window.innerWidth - 170) + 'px';
  msgCtx.style.top = Math.min(y, window.innerHeight - 150) + 'px';
}

messagesEl.addEventListener('contextmenu', e => {
  const t = e.target.closest('.msg-user, .msg-ai-wrap');
  if (!t) return;
  if (!t.dataset.msgId) return;
  e.preventDefault();
  e.stopPropagation();
  openMsgCtx(e.clientX, e.clientY, t);
});
msgCtx.addEventListener('click', e => {
  const item = e.target.closest('[data-mact]');
  const el = ctxMsgEl;      // 先捕获目标，再关闭菜单（closeMsgCtx 会清空 ctxMsgEl）
  if (!item || !el) return;
  const act = item.dataset.mact;
  closeMsgCtx();
  if (act === 'copy'){
    const text = el._text || el.textContent;
    if (text && text.trim()) navigator.clipboard.writeText(text.trim()).then(() => toast('已复制'), () => toast('复制失败'));
    else toast('暂无可复制的内容');
  } else if (act === 'edit'){
    handleMsgEdit(el, Number(el.dataset.msgId));
  } else if (act === 'regen'){
    regenTurn(el);
  } else if (act === 'del'){
    handleMsgDelete(el, Number(el.dataset.msgId));
  }
});
/* 点击他处 / 右击他处 / Esc 关闭消息右键菜单 */
document.addEventListener('click', e => { if (!e.target.closest('#msgCtxMenu')) closeMsgCtx(); });
document.addEventListener('contextmenu', e => { if (!e.target.closest('#msgCtxMenu')) closeMsgCtx(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMsgCtx(); });

/* 选中即复制：在消息区划选回复文字后，于选区旁浮出"复制选中"（DeepSeek 交互） */
let selCopyEl = null;
function hideSelCopy(){
  if (selCopyEl){ selCopyEl.remove(); selCopyEl = null; }
}
document.addEventListener('selectionchange', () => {
  hideSelCopy();
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return;
  const text = sel.toString().trim();
  if (!text) return;
  // 仅当选区位于消息区内才浮出（避免顶栏/别的区域误触发）
  if (!messagesEl.contains(sel.anchorNode)) return;
  const range = sel.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return;
  selCopyEl = document.createElement('button');
  selCopyEl.className = 'sel-copy-float';
  selCopyEl.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>复制选中`;
  // 定位在选区首个矩形右上角上方
  selCopyEl.style.left = Math.min(window.innerWidth - 130, Math.max(6, rect.left)) + 'px';
  selCopyEl.style.top = Math.max(6, rect.top - 34) + 'px';
  selCopyEl.addEventListener('click', () => {
    navigator.clipboard.writeText(text).then(
      () => { toast('已复制选中内容'); hideSelCopy(); window.getSelection().collapseToEnd(); },
      () => toast('复制失败，请手动复制'));
  });
  document.body.appendChild(selCopyEl);
});
/* 点击他处 / 滚轮滚动时收起浮层 */
document.addEventListener('mousedown', e => { if (selCopyEl && !selCopyEl.contains(e.target)) hideSelCopy(); });
messagesEl.addEventListener('scroll', hideSelCopy, true);
/* 重新生成：仅对最后一条回复生效，移除(用户消息+AI回复)后用当前模型重发同一问题 */
function regenTurn(wrap){
  if (sending){ toast('请等待当前回复完成后再重新生成'); return; }
  if (wrap !== messagesEl.querySelector('.msg-ai-wrap:last-child')){
    toast('只能重新生成最后一条回复');
    return;
  }
  if (!lastTurn){ toast('暂无法重新生成'); return; }
  const prev = wrap.previousElementSibling;
  if (prev && prev.classList.contains('msg-user')) prev.remove();
  wrap.remove();
  if (lastTurn.text) inputEl.value = lastTurn.text;
  attachedImages = lastTurn.images.slice();
  renderAttachments();
  autoResize();
  updateSendState();
  sendMessage();
}
/* 删除单条消息（用户/助手均可）：确认后调用后端删除，再移除气泡 */
async function handleMsgDelete(el, msgId){
  if (sending){ toast('请等待当前回复完成后再删除'); return; }
  if (!state.activeConv){ toast('暂无法删除'); return; }
  const ok = await showConfirm('删除这条消息？该操作不可恢复。', '删除消息', '删除');
  if (!ok) return;
  try{
    await apiFetch(`/conversations/${state.activeConv}/messages/${msgId}`, 'DELETE');
  }catch(err){
    toast('删除失败：' + err.message);
    return;
  }
  el.remove();
}
/* 编辑用户消息：回填文本 + 连同其后所有消息一并截断删除，由用户修改后再发送 */
async function handleMsgEdit(bubble, msgId){
  if (sending){ toast('请等待当前回复完成后再编辑'); return; }
  if (!state.activeConv){ toast('暂无法编辑'); return; }
  const text = (bubble.textContent || '').trim();
  if (!text){ toast('该消息没有可编辑的文本'); return; }
  // 收集待截断的消息 id：本条用户消息及其后方所有消息
  const victimIds = [];
  let node = bubble;
  while (node){
    const id = node.dataset && Number(node.dataset.msgId);
    if (id) victimIds.push(id);
    node = node.nextElementSibling;
  }
  try{
    await Promise.all(victimIds.map(id =>
      apiFetch(`/conversations/${state.activeConv}/messages/${id}`, 'DELETE')));
  }catch(err){
    toast('删除旧消息失败：' + err.message);
    return;
  }
  // 前端同步移除这些气泡
  node = bubble;
  while (node){
    const nx = node.nextElementSibling;
    node.remove();
    node = nx;
  }
  inputEl.value = text;
  attachedImages = [];
  renderAttachments();
  autoResize();
  updateSendState();
  inputEl.focus();
}

/* “+”弹出菜单 */
function closeAllPops(){
  document.querySelectorAll('.pop.open').forEach(p => p.classList.remove('open'));
}
function togglePop(pop){
  const wasOpen = pop.classList.contains('open');
  closeAllPops();
  if (!wasOpen) pop.classList.add('open');
}
$('plusBtn').addEventListener('click', e => { e.stopPropagation(); togglePop($('plusMenu')); });
$('plusMenu').addEventListener('click', e => {
  const item = e.target.closest('[data-act="send-image"]');
  if (!item) return;
  closeAllPops();
  if (!currentModelVision()){ toast('当前模型不支持图片'); return; }
  pickImages();
});

/* 模型选择胶囊（数据来自后端） */
function renderModelMenu(){
  if (!modelOptions.length){
    $('modelMenu').innerHTML = `<div class="pop-item disabled">暂无可用模型</div>`;
    return;
  }
  $('modelMenu').innerHTML = modelOptions.map((o, i) => `
    <div class="pop-item ${modelKey(o) === selectedModelKey ? 'selected' : ''}" data-opt="${i}">
      ${o.label}<span class="check">✓</span>
    </div>
  `).join('');
}
$('capsuleBtn').addEventListener('click', e => { e.stopPropagation(); renderModelMenu(); togglePop($('modelMenu')); });
$('modelMenu').addEventListener('click', e => {
  const item = e.target.closest('[data-opt]');
  if (!item) return;
  selectedModelKey = modelKey(modelOptions[Number(item.dataset.opt)]);
  updateCapsule();
  updateImgCtl(); // 切换模型后同步发图按钮可用性（依模型识图能力）
  closeAllPops();
});
/* 依据当前模型是否支持识图，启用/禁用"发送图片"，并可选中态提示。
   切到不支持视觉的模型时清空已附加图片（避免静默发送被后端忽略）。 */
function updateImgCtl(){
  const opt = currentModelOption();
  const vision = !!(opt && opt.vision);
  const btn = document.querySelector('.pop-item[data-act="send-image"]');
  if (btn) btn.classList.toggle('disabled', !vision);
  $('plusBtn').title = vision ? '添加' : '当前模型不支持图片';
  if (!vision && attachedImages.length) clearAttachments();
}
function currentModelVision(){ return !!(currentModelOption() && currentModelOption().vision); }
function updateCapsule(){
  const opt = currentModelOption();
  $('capsuleLabel').textContent = opt ? opt.short : '选择模型';
}

document.addEventListener('click', e => {
  if (!e.target.closest('.pop-wrap')) closeAllPops();
  if (!e.target.closest('#ctxMenu')) closeCtx();
});
document.addEventListener('contextmenu', e => {
  // 历史对话([data-conv])与历史任务(.task-item)右键时保持菜单，其余位置右键一律收起
  if (!e.target.closest('[data-conv], .task-item')) closeCtx();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape'){
    closeAllPops(); closeCtx(); closeRename();
    // 覆盖层按层级从顶到底关闭：用量明细 > 总账单 > 模型
    if ($('usageOv').classList.contains('open')) closeUsageOv();
    else if ($('billOv').classList.contains('open')) closeBillOv();
    else if ($('modelOv').classList.contains('open')) closeModelOv();
    closeConfirm(false);
    if (!$('pasteOk').disabled) $('pasteMask').classList.remove('open');
  }
});

/* ===================== 右侧：厂商/模型卡片（数据来自后端） ===================== */
const REFRESH_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>';

/* 延迟数值配色（数字变色，无额外文字）：<800ms 绿 / <2500ms 黄 / 其余红 / 无数据灰 */
function latencyClass(ms){
  if (ms == null) return 'lat-gray';
  if (ms < 800) return 'lat-green';
  if (ms < 2500) return 'lat-yellow';
  return 'lat-red';
}

/* B5：数据无变化则不重建 DOM（消除发送消息后的右侧卡片闪烁） */
let lastProvidersJson = '';
async function loadProviders(){
  try{
    const data = await apiFetch('/providers');
    providers = data.providers || [];
    rebuildModelOptions();
    const j = JSON.stringify(providers);
    if (j !== lastProvidersJson){
      lastProvidersJson = j;
      renderModels();
    }
  }catch(err){
    $('modelList').innerHTML = `<div class="empty-api" style="padding:12px 8px">${err.message}</div>`;
    toast(err.message);
  }
}

/* 手动检测：验证每个 API Key 是否仍有效（免费接口），顺带刷新主 API 余额/延迟 */
async function checkProvider(pid, btn){
  if (btn){ btn.classList.add('spin'); btn.disabled = true; }
  try{
    const data = await apiFetch(`/providers/${pid}/check`, 'POST');
    const idx = providers.findIndex(p => p.id === pid);
    if (idx >= 0 && data.provider){
      providers[idx] = data.provider;
      rebuildModelOptions();
      lastProvidersJson = ''; // 强制重渲
      renderModels();
      lastProvidersJson = JSON.stringify(providers);
    }
    const bad = (data.results || []).filter(r => !r.ok);
    if (bad.length){
      toast(`检测到 ${bad.length} 个 API 异常：${bad[0].error || '验证失败'}`);
    } else {
      toast('检测完成，所有 API 均有效');
    }
  }catch(err){
    toast('检测失败：' + err.message);
  }finally{
    if (btn){ btn.classList.remove('spin'); btn.disabled = false; }
  }
}

function rebuildModelOptions(){
  modelOptions = [];
  providers.forEach(p => {
    if (p.apis && p.apis.length){
      (p.models || []).forEach(m => {
        const short = m.display_name || m.model_id;
        modelOptions.push({
          provider_id: p.id,
          model_id: m.model_id,
          label: `${p.display_name} · ${short}`,
          short,
          vision: !!m.vision, // 是否支持识图：后端驱动，控制发图按钮
        });
      });
    }
  });
  if (!modelOptions.some(o => modelKey(o) === selectedModelKey)){
    selectedModelKey = modelOptions.length ? modelKey(modelOptions[0]) : null;
  }
  updateCapsule();
  syncChatState();
}

function renderModels(){
  const listEl = $('modelList');
  $('panelHead').textContent = `模型 · ${providers.length}`;
  if (!providers.length){
    listEl.innerHTML = `<div class="empty-api" style="padding:12px 8px">暂无厂商</div>`;
    return;
  }
  listEl.innerHTML = providers.map((p, idx) => {
    const open = openStates[p.id] !== undefined ? openStates[p.id] : (idx === 0);
    openStates[p.id] = open;
    const dot = STATUS_COLOR[p.status] || 'gray';
    const debt = p.balance != null && p.balance < 0;
    const head = `
      <div class="model-head" data-toggle="${p.id}">
        <span class="model-arrow"><svg viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
        <span class="p-icon">${providerIcon(p.name)}</span>
        <span class="model-name">${p.display_name}</span>
        <span class="model-status st-${dot}">${p.status}</span>
        <span class="dot ${dot}"></span>
      </div>
    `;
    if (!open) return `<div class="model" data-id="${p.id}">${head}</div>`;

    let body;
    if (p.apis && p.apis.length){
      const stats = `
        <div class="stat latency-stat">
          <span class="k">延迟</span>
          <span class="v latency-val ${latencyClass(p.latency_ms)}">${p.latency_ms != null ? p.latency_ms + 'ms' : '—'}</span>
        </div>
        <div class="stat"><span class="k">余额</span><span class="v ${debt ? 'debt' : ''}">${p.balance != null ? '¥' + p.balance : '—'}</span>${debt ? '<span class="debt-badge">已欠费</span>' : ''}</div>
        <div class="stat"><span class="k">今日调用</span><span class="v">${p.today_calls} 次</span></div>
        <div class="stat"><span class="k">命中缓存</span><span class="v">${fmtToken(p.cache_hit_tokens)} Token</span></div>
        <div class="stat"><span class="k">未命中缓存</span><span class="v">${fmtToken(p.cache_miss_tokens)} Token</span></div>
        <div class="refresh-row">
          <button class="refresh-line" data-check="${p.id}" title="重新检测连接与延迟">${REFRESH_SVG}<span>刷新检测</span></button>
        </div>
      `;
      const modelRows = (p.models || []).map(m => `
        <div class="model-row">
          <span class="m-icon">${providerIcon(p.name)}</span>
          <span class="m-name">${m.display_name || m.model_id}</span>
          <span class="m-ctx">${m.context_window ? fmtCtx(m.context_window) + ' 上下文' : ''}</span>
        </div>
      `).join('');
      const apiRows = p.apis.map(a => `
        <div class="api-row">
          <span class="api-dot ${a.is_primary ? 'solid' : 'hollow'}" data-set-primary="${p.id}:${a.id}" title="设为主 API"></span>
          <span class="api-label">${a.is_primary ? '主 API' : '备用 API'}</span>
          ${a.decrypt_failed
            ? '<span class="api-key err" title="加密密钥已变更，无法解密">密钥无法解密，请移除后重新粘贴</span>'
            : `<span class="api-key">${escHtml(a.masked_key)}</span>`}
          <button class="api-remove" data-del-api="${p.id}:${a.id}">移除</button>
        </div>
      `).join('');
      body = `
        <div class="model-body">
          <div class="divider"></div>
          ${stats}
          <div class="sec-title">模型</div>
          ${modelRows || '<div class="empty-api">暂无模型</div>'}
          <div class="sec-title">API</div>
          ${apiRows}
          <div class="btn-row">
            <button class="ghost-btn" data-act="add-api" data-id="${p.id}">+ 添加备用 API</button>
            <button class="ghost-btn" data-act="log" data-id="${p.id}">用量明细</button>
            ${p.recharge_url ? `<button class="ghost-btn" data-act="recharge" data-id="${p.id}">充值</button>` : ''}
          </div>
        </div>
      `;
    } else {
      body = `
        <div class="model-body">
          <div class="divider"></div>
          <div class="empty-api">尚未添加 API</div>
          <div class="btn-row">
            <button class="ghost-btn" data-act="apply" data-id="${p.id}">申请 API</button>
            <button class="ghost-btn" data-act="paste" data-id="${p.id}">粘贴 API</button>
          </div>
        </div>
      `;
    }
    return `<div class="model open" data-id="${p.id}">${head}${body}</div>`;
  }).join('');
}

$('modelList').addEventListener('click', async e => {
  // 刷新/检测按钮
  const chk = e.target.closest('[data-check]');
  if (chk){
    e.stopPropagation();
    checkProvider(Number(chk.dataset.check), chk);
    return;
  }
  // 圆点：切换主 API
  const dot = e.target.closest('[data-set-primary]');
  if (dot){
    const [pid, aid] = dot.dataset.setPrimary.split(':').map(Number);
    try{
      await apiFetch(`/providers/${pid}/apis/${aid}/primary`, 'PUT');
      toast('已切换主 API');
      loadProviders();
    }catch(err){ toast(err.message); }
    return;
  }
  // 移除 API（二次确认）
  const del = e.target.closest('[data-del-api]');
  if (del){
    const [pid, aid] = del.dataset.delApi.split(':').map(Number);
    const p = providers.find(x => x.id === pid);
    const a = p && p.apis.find(x => x.id === aid);
    const ok = await showConfirm(
      `确定移除 API「${a ? a.name : aid}」吗？其历史调用日志将一并删除。`,
      '移除 API', '移除');
    if (!ok) return;
    try{
      await apiFetch(`/providers/${pid}/apis/${aid}`, 'DELETE');
      toast('已移除该 API');
      loadProviders();
    }catch(err){ toast(err.message); }
    return;
  }
  // 操作按钮
  const actBtn = e.target.closest('[data-act]');
  if (actBtn){
    const act = actBtn.dataset.act;
    const pid = Number(actBtn.dataset.id);
    if (act === 'add-api' || act === 'paste'){ openPaste(pid); }
    else if (act === 'apply'){ applyProvider(pid); }
    else if (act === 'recharge'){ openRecharge(pid); }
    else if (act === 'log'){ openUsage(pid); }
    return;
  }
  // 展开/收起（仅切换 UI，不触发网络请求；检测需手动点"检测并刷新"）
  const head = e.target.closest('[data-toggle]');
  if (head){
    const id = Number(head.dataset.toggle);
    openStates[id] = !openStates[id];
    renderModels();
  }
});

$('addModelBtn').disabled = true; // 置灰而非误导性提示；后续接入多厂商后启用
$('addModelBtn').title = '更多厂商接入开发中';
// 注意：必须用箭头函数包裹，直接传 openBilling 会把 MouseEvent 当成 days 传入，
// 导致 days != null 成立、billDays 被覆盖成事件对象，请求变为 /billing?days=[object MouseEvent] → 422 

/* ===================== 桌面壳·受控内部窗口（申请 / 充值） ===================== */
// 桌面壳可用时在 Monstera 内部受控窗口加载官方页；浏览器打开时回退系统浏览器新标签
const hasDesktop = () => !!(window.monstera && window.monstera.openInternalWindow);
function openDesktopWindow(url, kind){
  if (!url){ toast('该厂商暂未配置页面地址'); return false; }
  if (hasDesktop()) window.monstera.openInternalWindow(url, kind);
  else window.open(url, '_blank');
  return true;
}

/* 余额轮询：打开充值窗口后后台轮询该厂商余额，检测到上涨即停止轮询并刷新显示 */
const _rechargePoll = {};                // pid -> { timer, startedAt, unsub }
const RECHARGE_POLL_MS = 5000;           // 轮询间隔
const RECHARGE_POLL_TIMEOUT = 5 * 60 * 1000; // 最长等待 5 分钟
function stopRechargePolling(pid){
  const job = _rechargePoll[pid];
  if (!job) return;
  if (job.timer) clearInterval(job.timer);
  if (job.unsub) job.unsub();
  delete _rechargePoll[pid];
}
async function startRechargePolling(pid){
  const p = providers.find(x => x.id === pid);
  if (!p) return;
  const base = p.balance;                // 充值前基线（可能为 null）
  stopRechargePolling(pid);              // 重复进入先重置，避免并发轮询
  const unsub = hasDesktop()
    ? window.monstera.onInternalWindowClosed(({ kind }) => {
        if (kind === 'recharge') stopRechargePolling(pid);
      })
    : null;
  const job = { startedAt: Date.now(), unsub };
  _rechargePoll[pid] = job;
  job.timer = setInterval(async () => {
    if (Date.now() - job.startedAt > RECHARGE_POLL_TIMEOUT){ stopRechargePolling(pid); return; }
    try{
      const data = await apiFetch('/providers');
      const cur = (data.providers || []).find(x => x.id === pid);
      const balance = (cur && cur.balance != null) ? cur.balance : null;
      const increased = balance != null && (base == null || balance > base + 0.001);
      if (increased){
        stopRechargePolling(pid);
        toast(`充值成功，余额已更新为 ¥${balance}`);
        loadProviders();
      }
    }catch(_){}
  }, RECHARGE_POLL_MS);
}
function openRecharge(pid){
  const p = providers.find(x => x.id === pid);
  if (!openDesktopWindow(p && p.recharge_url, 'recharge')) return;
  toast('已打开官方充值页，支付完成后余额会自动刷新');
  startRechargePolling(pid);
}

/* ===================== 申请 API：直接前往厂商官网（不弹介绍页） ===================== */
function applyProvider(pid){
  const p = providers.find(x => x.id === pid);
  // 直接在该厂商官网打开（桌面壳内内部窗口秒开 + 加载遮罩；浏览器回退系统新标签）
  if (!openDesktopWindow(p && p.docs_url, 'apply')) return;
  toast('已打开 ' + (p ? p.display_name : '') + ' 开放平台，登录后创建 API Key 再粘贴');
}

/* ===================== 粘贴 API 弹窗 ===================== */
function setPasteStatus(cls, msg){
  const el = $('pasteStatus');
  el.className = 'paste-status' + (cls ? ' ' + cls : '');
  el.textContent = msg;
}
function openPaste(pid){
  pasteProviderId = pid;
  const p = providers.find(x => x.id === pid);
  $('pasteTitle').textContent = `粘贴 ${p ? p.display_name : ''} API`;
  $('pasteName').value = (p && p.apis && p.apis.length) ? '备用 API' : '主 API';
  $('pasteKey').value = '';
  setPasteStatus('', '');
  $('pasteOk').disabled = false;
  $('pasteMask').classList.add('open');
  setTimeout(() => $('pasteKey').focus(), 30);
}
async function submitPaste(){
  const key = $('pasteKey').value.trim();
  if (!key){ setPasteStatus('err', '请先粘贴 API Key'); return; }
  const btn = $('pasteOk');
  btn.disabled = true;
  setPasteStatus('busy', '验证中…');
  try{
    const data = await apiFetch(`/providers/${pasteProviderId}/apis`, 'POST', {
      api_key: key,
      name: $('pasteName').value.trim() || undefined,
    });
    setPasteStatus('ok', '验证成功，已保存并同步模型列表');
    toast(`API 已添加${data.balance != null ? '，余额 ¥' + data.balance : ''}`);
    setTimeout(() => {
      $('pasteMask').classList.remove('open');
      loadProviders();
    }, 600);
  }catch(err){
    setPasteStatus('err', err.message);
    btn.disabled = false;
  }
}
$('keyEye').addEventListener('click', () => {
  const k = $('pasteKey');
  const show = k.type === 'password';
  k.type = show ? 'text' : 'password';
  $('keyEye').textContent = show ? '🙈' : '👁';
});
$('pasteOk').addEventListener('click', submitPaste);
$('pasteCancel').addEventListener('click', () => {
  if (!$('pasteOk').disabled) $('pasteMask').classList.remove('open');
});
$('pasteMask').addEventListener('click', e => {
  if (e.target === $('pasteMask') && !$('pasteOk').disabled) $('pasteMask').classList.remove('open');
});
$('pasteKey').addEventListener('keydown', e => {
  if (e.key === 'Enter') submitPaste();
});

/* ===================== 右侧面板：调用日志（替换模型列表区域） ===================== */
function fmtFullTime(iso){
  if (!iso) return '—';
  const d = new Date(iso);
  const p = n => String(n).padStart(2, '0');
  // 参考主流平台（OpenAI/DeepSeek 等）：完整 YYYY-MM-DD HH:MM:SS
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
/* ===================== 全屏视图：用量明细（单厂商用量账单总结） ===================== */
let usageQ = { pid: 0, days: 7, status: '', offset: 0, limit: 50, total: 0, loaded: [] };
let usageSum = null;
const USAGE_PERIODS = [[1, '今日'], [7, '近7天'], [30, '近30天']];

async function openUsage(pid){
  const p = providers.find(x => x.id === pid);
  usageQ = { pid, days: 7, status: '', offset: 0, limit: 50, total: 0, loaded: [] };
  usageSum = null;
  $('usageTitle').textContent = `用量明细 · ${p ? p.display_name : ''}`;
  $('usageBody').innerHTML = '<div class="empty-api" style="padding:16px">加载中…</div>';
  openUsageOv(); // 右侧 80% 展开，盖在模型面板之上，不关闭模型面板
  try{ await refreshUsage(); }
  catch(err){ $('usageBody').innerHTML = `<div class="empty-api" style="padding:16px">${err.message}</div>`; }
}
/* 汇总（billing）+ 请求首屏（logs）并行拉取后渲染 */
async function refreshUsage(){
  const q = usageQ;
  const [sum, list] = await Promise.all([
    apiFetch(`/billing?days=${q.days}&provider_id=${q.pid}`),
    fetchUsePage(),
  ]);
  usageSum = sum;
  q.total = list.total; q.loaded = list.logs; q.offset = (list.logs || []).length;
  renderUsage();
}
async function fetchUsePage(){
  const q = usageQ;
  const params = new URLSearchParams({ provider_id: q.pid, limit: q.limit, offset: q.offset, days: q.days });
  if (q.status) params.set('status', q.status);
  return apiFetch(`/logs?${params}`);
}
/* 时段 / 仅失败变化：重置并重拉汇总+首屏 */
function usageQuery(){
  const q = usageQ; q.offset = 0; q.loaded = [];
  refreshUsage().catch(err => { $('usageBody').innerHTML = `<div class="empty-api" style="padding:16px">${err.message}</div>`; });
}
async function usageLoadMore(){
  const q = usageQ;
  const data = await fetchUsePage();
  q.total = data.total; q.loaded = q.loaded.concat(data.logs || []); q.offset += (data.logs || []).length;
  renderUsage();
}
function renderUsage(){
  const q = usageQ, b = usageSum || {};
  const t = b.total_tokens || {};
  const periodBtns = USAGE_PERIODS.map(([d, label]) =>
    `<button class="bill-period-btn ${d === q.days ? 'on' : ''}" data-useday="${d}">${label}</button>`).join('');
  const tokensLine = `<div class="bill-tokens">
    <span>输入（未命中缓存）<b>${fmtToken(t.input || 0)}</b></span>
    <span>命中缓存<b>${fmtToken(t.cached || 0)}</b></span>
    <span>输出<b>${fmtToken(t.output || 0)}</b></span></div>`;
  const modelRows = (b.by_model || []).map(row => `<tr>
    <td>${escHtml(row.model_id)}</td>
    <td class="num">${row.calls}</td>
    <td class="num">${row.cost != null ? '¥' + Number(row.cost).toFixed(6) : '—'}</td>
    <td class="num">${(Number(row.success_rate || 0) * 100).toFixed(0)}%</td>
    <td class="num">${fmtToken(row.tokens.input)}</td>
    <td class="num">${fmtToken(row.tokens.output)}</td></tr>`).join('');
  const reqRows = q.loaded.map(l => `<tr>
    <td>${fmtFullTime(l.created_at)}</td>
    <td>${escHtml(l.model_id || '')}</td>
    <td class="num">${fmtToken(l.cache_miss_tokens)}</td>
    <td class="num">${fmtToken(l.cache_hit_tokens)}</td>
    <td class="num">${fmtToken(l.response_tokens)}</td>
    <td class="num">${l.cost == null ? '<span style="color:var(--yellow)">未知</span>' : '¥' + l.cost.toFixed(6)}</td>
    <td class="num">${l.latency_ms}ms</td>
    <td>${l.success ? '<span class="ok-tag">成功</span>' : `<span class="fail-tag" title="${escHtml(l.error_message || '')}">失败</span>`}</td></tr>`).join('');
  const more = q.offset < q.total
    ? `<button class="log-more" id="usageMore">加载更多（还剩 ${q.total - q.offset} 条）</button>` : '';
  $('usageBody').innerHTML = `
    <div class="bill-periods">${periodBtns}
      <label class="log-chk" style="margin:0"><input type="checkbox" id="usageFailOnly" ${q.status === 'failed' ? 'checked' : ''}> 仅失败</label>
      <span class="bill-range">${b.date_from} ~ ${b.date_to}</span>
    </div>
    <div class="bill-cards">
      <div class="bill-card big"><b>${b.total_calls}</b><span>调用次数</span></div>
      <div class="bill-card big"><b>¥${Number(b.total_cost || 0).toFixed(6)}</b><span>总花费</span></div>
      <div class="bill-card big"><b>${(Number(b.success_rate || 0) * 100).toFixed(0)}%</b><span>成功率</span></div>
      <div class="bill-card big"><b>${fmtToken(t.output || 0)}</b><span>输出 Token</span></div>
    </div>
    ${tokensLine}
    <div class="sec-label">按模型</div>
    ${billTable(['模型', '调用', '花费', '成功率', '输入', '输出'], modelRows, '该时段暂无调用')}
    <div class="sec-label">每日花费趋势</div>
    ${renderBillChart(b.trend)}
    <div class="sec-label">请求明细 · ${q.total} 条</div>
    ${billTable(['时间', '模型', '输入', '缓存', '输出', '费用', '延迟', '结果'], reqRows, '暂无请求记录')}
    ${more}`;
}
/* 用量明细筛选 / 分页事件（事件委托） */
$('usageBody').addEventListener('click', e => {
  const seg = e.target.closest('[data-useday]');
  if (seg){ usageQ.days = Number(seg.dataset.useday); usageQuery(); return; }
  if (e.target.closest('#usageMore')) usageLoadMore().catch(err => toast('加载更多失败：' + err.message));
});
$('usageBody').addEventListener('change', e => {
  if (e.target.id === 'usageFailOnly'){ usageQ.status = e.target.checked ? 'failed' : ''; usageQuery(); }
});

/* ===================== 记忆中枢（本地、离线、可编辑记忆文档） =====================
   ⚠️ 入口按钮（记忆中枢 / 查看账单 旁的 memBtn）已从模型界面移除，本子系统保留待后续启用；
      当前无可达调用方（除内部 openMemoryDoc/openMemoryFile 委托），切勿删除模块本体。 */
function fmtMemSize(n){
  if (n == null) return '—';
  n = Number(n);
  if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB';
  if (n >= 1024) return Math.round(n / 1024) + ' KB';
  return n + ' B';
}
let memoryActive = null; // 当前打开的记忆文档 id
async function openMemory(){
  // 记忆中枢暂未开放：仅展开面板并显示"开发中"占位，不加载真实记忆
  $('modelPanel').style.display = 'none';
  $('memoryPanel').classList.add('open');
  $('memoryTitle').textContent = '记忆中枢';
  $('memoryBody').innerHTML = `
    <div class="mem-wip">
      <div class="mem-wip-ic"></div>
      <div class="mem-wip-t">开发中</div>
      <div class="mem-wip-s">记忆中枢暂未开放，敬请期待后续版本。</div>
    </div>`;
}
async function renderMemoryList(){
  $('memoryTitle').textContent = '记忆中枢';
  $('memoryBody').innerHTML = '<div class="empty-api" style="padding:16px">加载中…</div>';
  let statusHtml = '';
  try{
    const st = await apiFetch('/memory/status');
    const lm = (st.local_model || {});
    if (lm.ready){
      statusHtml = `<div class="mem-lm ok">本地整理模型已就绪 · ${escHtml(lm.model_name || '')}</div>`;
    } else if (lm.enabled){
      statusHtml = `<div class="mem-lm warn">已开启本地整理模型，但模型文件未就绪，暂用规则压缩。</div>`;
    } else {
      statusHtml = `<div class="mem-lm off">记忆整理引擎：规则压缩（放入本地模型并开启开关后走本地模型）</div>`;
    }
  }catch(_){}
  const head = `<div class="mem-status">${statusHtml}</div>`;
  try{
    const data = await apiFetch('/memory');
    const docs = data.docs || [];
    memoryActive = null;
    if (!docs.length){
      $('memoryBody').innerHTML = head +
        '<div class="empty-api" style="padding:20px">暂无记忆文档。<br><br>与模型对话后，Monstera 会在本地把要点自动整理为文档（仅存本地，不进任何云端）。</div>';
      return;
    }
    $('memoryBody').innerHTML = head + docs.map(d => {
      const linked = (d.writing_conversations || []).filter(w => w.conversation_id !== d.conversation_id);
      const linkNote = linked.length
        ? `<div class="mem-inherit">由 ${linked.length} 个后续对话继承续写</div>` : '';
      return `
      <div class="mem-item" data-mem-id="${d.id}">
        <div class="mem-item-top">
          <span class="mem-ic" title="${d.engine === 'local-model' ? '由本地模型整理' : (d.engine ? '由规则压缩整理' : '尚未整理')}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </span>
          <span class="mem-title">${escHtml(d.title || ('对话 ' + d.conversation_id))}</span>
          <button class="mem-del" data-mem-del="${d.id}" data-mem-title="${escHtml(d.title || ('对话 ' + d.conversation_id))}" title="删除这份记忆文档">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          </button>
        </div>
        <div class="mem-meta">${d.status === 'failed' ? '整理失败' : (d.engine ? (d.engine === 'local-model' ? '本地模型' : '规则压缩') : '待整理')} · ${fmtFullTime(d.updated_at)} · ${fmtMemSize(d.size_bytes)}</div>
        ${linkNote}
      </div>`;
    }).join('');
  }catch(err){
    $('memoryBody').innerHTML = `<div class="empty-api" style="padding:16px">${err.message}</div>`;
  }
}
async function openMemoryDoc(id){
  memoryActive = id;
  $('memoryTitle').textContent = '记忆文档';
  $('memoryBody').innerHTML = '<div class="empty-api" style="padding:16px">加载中…</div>';
  try{
    const d = await apiFetch('/memory/' + id);
    $('memoryBody').innerHTML = `
      <div class="mem-detail">
        <div class="mem-detail-head">
          <button class="back-btn" id="memToList">
            <svg viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            返回列表
          </button>
          <div class="mem-detail-actions">
            <button class="ghost-btn" data-mem-open="${d.id}">打开文件</button>
            <button class="ghost-btn" data-mem-save="${d.id}">保存修改</button>
            <button class="ghost-btn danger-ghost" data-mem-del="${d.id}" data-mem-title="${escHtml(d.title || ('对话 ' + d.conversation_id))}">删除文档</button>
          </div>
        </div>
        <input id="memTitleInput" class="mem-title-input" maxlength="40" value="${escHtml(d.title)}" placeholder="文档标题">
        <textarea id="memContent" class="mem-editor" spellcheck="false">${escHtml(d.content)}</textarea>
        <div class="mem-path">本地路径：${escHtml(d.path)}</div>
      </div>`;
  }catch(err){
    $('memoryBody').innerHTML = `<div class="empty-api" style="padding:16px">${err.message}</div>`;
  }
}
async function saveMemoryDoc(id){
  const content = $('memContent').value;
  const title = $('memTitleInput').value.trim();
  try{
    const r = await apiFetch('/memory/' + id, 'PUT', { content, title: title || undefined });
    toast('已保存到本地记忆文档');
    if ($('memPathTxt') && title) $('memPathTxt').textContent = '本地路径：' + r.path;
  }catch(err){ toast(err.message); }
}
async function openMemoryFile(id){
  try{
    await apiFetch('/memory/' + id + '/open', 'POST');
    toast('已用系统默认程序打开记忆文档');
  }catch(err){ toast(err.message); }
}
async function deleteMemoryDoc(id, title){
  const ok = await showConfirm(
    `确定删除记忆文档「${title}」吗？本地对应的 .md 文件将一并删除，且无法恢复。若有对话继承它，之后将新建空白文档续写。`,
    '删除记忆文档', '删除');
  if (!ok) return;
  try{
    await apiFetch('/memory/' + id, 'DELETE');
    toast('已删除记忆文档（本地文件已同步移除）');
    renderMemoryList();
  }catch(err){ toast(err.message); }
}
// 面板内点击（列表项 / 删除 / 返回列表 / 打开文件 / 保存）
$('memoryBody').addEventListener('click', async e => {
  const delBtn = e.target.closest('[data-mem-del]');
  if (delBtn){
    e.preventDefault(); e.stopPropagation();
    await deleteMemoryDoc(Number(delBtn.dataset.memDel), (delBtn.dataset.memTitle || '该文档'));
    return;
  }
  const item = e.target.closest('[data-mem-id]');
  if (item){ openMemoryDoc(Number(item.dataset.memId)); return; }
  if (e.target.closest('#memToList')){ renderMemoryList(); return; }
  const openBtn = e.target.closest('[data-mem-open]');
  if (openBtn){ openMemoryFile(Number(openBtn.dataset.memOpen)); return; }
  const saveBtn = e.target.closest('[data-mem-save]');
  if (saveBtn){ saveMemoryDoc(Number(saveBtn.dataset.memSave)); return; }
});
$('memoryBack').addEventListener('click', () => {
  $('memoryPanel').classList.remove('open');
  $('modelPanel').style.display = 'flex';
});

/* ===================== 全屏视图：总账单（隐藏三栏） ===================== */
let billDays = 1; // 1=今日 / 7 / 30
const BILL_PERIODS = [[1, '今日'], [7, '近7天'], [30, '近30天']];

/* 每日花费趋势：纯 SVG 柱状图（无第三方库），缺失天补零后柱高连续 */
function renderBillChart(trend){
  const n = (trend || []).length;
  if (!n) return '<div class="empty-api" style="padding:8px">暂无数据</div>';
  const maxCost = Math.max(...trend.map(t => t.cost), 0);
  const W = 720, H = 132, pad = 10, baseY = H - pad;
  const bw = (W - pad * 2) / n;
  const bars = trend.map((t, i) => {
    const h = maxCost > 0 ? (t.cost / maxCost) * (H - pad * 2 - 16) : 2;
    const x = pad + i * bw;
    const y = baseY - (h || 2);
    return `<rect x="${(x + 1).toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(bw - 4, 3).toFixed(1)}" height="${(h || 2).toFixed(1)}" rx="1.5" fill="url(#billGrad)" opacity="${t.calls ? 0.95 : 0.1}"><title>${escHtml(t.date)}　¥${t.cost.toFixed(4)}　${t.calls} 次调用</title></rect>`;
  }).join('');
  const labels = trend.map((t, i) => {
    const shown = n <= 7 ? t.date.slice(5) : (i % 2 === 0 && n <= 15 ? t.date.slice(5) : '');
    return `<text x="${(pad + i * bw + bw / 2).toFixed(1)}" y="${H - 3}" font-size="8.5" fill="var(--dim)" text-anchor="middle">${shown || ''}</text>`;
  }).join('');
  return `<svg viewBox="0 0 ${W} ${H}" class="bill-chart" preserveAspectRatio="xMidYMid meet">
    <defs><linearGradient id="billGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e3c79f"/><stop offset="1" stop-color="#8a6d3b" stop-opacity=".3"/>
    </linearGradient></defs>
    ${bars}${labels}
  </svg>`;
}

function billTable(headers, rows, empty){
  return `<div class="tbl-wrap"><table class="tbl">
    <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
    <tbody>${rows || `<tr><td colspan="${headers.length}" style="text-align:center;color:var(--dim)">${empty}</td></tr>`}</tbody>
  </table></div>`;
}

async function openBilling(days, keepOpen){
  if (days != null) billDays = days;
  $('billBody').innerHTML = '<div class="empty-api" style="padding:16px">加载中…</div>';
  if (!keepOpen) openBillOv(); // 右侧 80% 覆盖层（不透明、不可拖动）
  try{
    const [b, logsData] = await Promise.all([
      apiFetch(`/billing?days=${billDays}`),
      apiFetch(`/logs?days=${billDays}&limit=10`),
    ]);
    const t = b.total_tokens || {};
    const periodBtns = BILL_PERIODS.map(([d, label]) =>
      `<button class="bill-period-btn ${d === billDays ? 'on' : ''}" data-bill-day="${d}">${label}</button>`).join('');

    const provRows = (b.by_provider || []).map(row => `<tr>
      <td>${escHtml(row.display_name || row.provider_id)}</td>
      <td class="num">${row.calls}</td>
      <td class="num">${row.cost != null ? '¥' + Number(row.cost).toFixed(6) : '—'}</td>
      <td class="num">${(Number(row.success_rate || 0) * 100).toFixed(0)}%</td>
      <td class="num">${fmtToken(row.tokens.input)}</td>
      <td class="num">${fmtToken(row.tokens.cached)}</td>
      <td class="num">${fmtToken(row.tokens.output)}</td></tr>`).join('');
    const modelRows = (b.by_model || []).map(row => `<tr>
      <td>${escHtml(row.model_id)}</td>
      <td style="color:var(--dim)">${escHtml(row.display_name || '')}</td>
      <td class="num">${row.calls}</td>
      <td class="num">${row.cost != null ? '¥' + Number(row.cost).toFixed(6) : '—'}</td>
      <td class="num">${(Number(row.success_rate || 0) * 100).toFixed(0)}%</td>
      <td class="num">${fmtToken(row.tokens.input)}</td>
      <td class="num">${fmtToken(row.tokens.output)}</td></tr>`).join('');

    // 最近请求记录（参考主流平台总用量页）：逐条精确记录时间
    const reqRows = (logsData?.logs || []).map(l => `<tr>
      <td>${fmtFullTime(l.created_at)}</td>
      <td>${escHtml(l.model_id || '')}</td>
      <td class="num">${fmtToken(l.cache_miss_tokens)}</td>
      <td class="num">${fmtToken(l.cache_hit_tokens)}</td>
      <td class="num">${fmtToken(l.response_tokens)}</td>
      <td class="num">${l.cost == null ? '<span style="color:var(--yellow)">未知</span>' : '¥' + l.cost.toFixed(6)}</td>
      <td class="num">${l.latency_ms}ms</td>
      <td>${l.success ? '<span class="ok-tag">成功</span>' : `<span class="fail-tag" title="${escHtml(l.error_message || '')}">失败</span>`}</td></tr>`).join('');

    $('billBody').innerHTML = `
      <div class="bill-periods">${periodBtns}<span class="bill-range">${b.date_from} ~ ${b.date_to} · 共 ${b.days} 天</span></div>
      <div class="bill-cards">
        <div class="bill-card big"><b>${b.total_calls}</b><span>调用次数</span></div>
        <div class="bill-card big"><b>¥${Number(b.total_cost || 0).toFixed(6)}</b><span>总花费</span></div>
        <div class="bill-card big"><b>${(Number(b.success_rate || 0) * 100).toFixed(0)}%</b><span>成功率</span></div>
        <div class="bill-card big"><b>${fmtToken(t.output || 0)}</b><span>输出 Token</span></div>
      </div>
      <div class="bill-tokens">
        <span>输入（未命中缓存）<b>${fmtToken(t.input || 0)}</b></span>
        <span>命中缓存<b>${fmtToken(t.cached || 0)}</b></span>
        <span>输出<b>${fmtToken(t.output || 0)}</b></span>
      </div>
      <div class="sec-label">每日花费趋势</div>
      ${renderBillChart(b.trend)}
      <div class="sec-label">按厂商</div>
      ${billTable(['厂商', '调用', '花费', '成功率', '输入', '缓存', '输出'],
        provRows, '该时段暂无调用')}
      <div class="sec-label">按模型</div>
      ${billTable(['模型', '厂商', '调用', '花费', '成功率', '输入', '输出'],
        modelRows, '该时段暂无调用')}
      <div class="sec-label">最近请求记录 · ${logsData?.total || 0} 条</div>
      ${billTable(['记录时间', '模型', '输入', '缓存', '输出', '费用', '延迟', '结果'],
        reqRows, '该时段暂无请求记录')}`;
  }catch(err){
    $('billBody').innerHTML = `<div class="empty-api" style="padding:16px">${err.message}</div>`;
  }
}
/* 账单页切换时间维度（事件委托）：同一次不重建视图，仅重新拉取数据 */
$('billBody').addEventListener('click', e => {
  const btn = e.target.closest('.bill-period-btn');
  if (!btn) return;
  openBilling(Number(btn.dataset.billDay), true);
});

/* ===================== 新三栏布局：模式 / 折叠 / 拖拽 / 覆盖层 / 空态 ===================== */
const appEl = document.querySelector('.app');
const chatAreaEl = $('chatArea');
const sidebarEl = $('sidebar');
const agentPaneEl = $('agentPane');
const nmBox = $('noModelBox');

/* ---------- 自绘标题栏 & 手动缩放（桌面壳无边框窗口） ---------- */
const wc = window.monstera && window.monstera.windowControls;
if (wc){
  const wcMin = $('wcMin'), wcMax = $('wcMax'), wcClose = $('wcClose'), rsz = $('resizeHandle');
  if (wcMin) wcMin.addEventListener('click', () => wc.minimize());
  if (wcClose) wcClose.addEventListener('click', () => wc.close());
  if (wcMax){
    wcMax.addEventListener('click', () => wc.toggleMaximize());
    const syncMax = (v) => {
      wcMax.classList.toggle('is-max', !!v);
      document.documentElement.classList.toggle('monstera-max', !!v);
    };
    wc.isMaximized().then(syncMax).catch(()=>{});
    wc.onMaximizedChange(syncMax);
  }
  /* 双击标题栏空白区等效最大化/还原（折叠钮所在区域除外，避免连点触发最大化） */
  const winBar = $('winBar');
  if (winBar) winBar.addEventListener('dblclick', (e) => {
    if (e.target.closest('.winbar-title, .winbar-controls')) return;
    wc.toggleMaximize();
  });
  /* 右下角手柄拖动缩放 */
  if (rsz){
    let dragging = false, sx = 0, sy = 0, bw = 1280, bh = 820;
    rsz.addEventListener('mousedown', (e) => {
      dragging = true; sx = e.screenX; sy = e.screenY;
      wc.getSize().then(([w, h]) => { bw = w; bh = h; }).catch(()=>{});
      e.preventDefault();
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      wc.setSize(bw + (e.screenX - sx), bh + (e.screenY - sy), true);
    });
    window.addEventListener('mouseup', () => { dragging = false; });
  }
}

/* ---------- 模式切换：聊天模式 / Agent 模式（默认聊天） ---------- */
const modeBtns = document.querySelectorAll('.mode-btn');
function setMode(mode){
  const isAgent = mode === 'agent';
  appEl.classList.toggle('mode-agent', isAgent);
  modeBtns.forEach(b => b.classList.toggle('on', b.dataset.mode === mode));
  // 侧栏新建按钮按模式切换文案：聊天模式「+ 新对话」/ Agent 模式「+ 新任务」
  const ncBtn = $('newChatBtn');
  if (ncBtn) ncBtn.textContent = isAgent ? '+ 新任务' : '+ 新对话';
  setAgentPane(false);   // 执行面板默认折叠：切到 Agent 模式下也是收起，由右上角折叠钮手动展开
  // Phase 4：Agent 模式下底部输入框变任务描述栏，并载入历史任务
  const inputEl0 = $('input');
  if (inputEl0) inputEl0.placeholder = isAgent ? '描述你要完成的任务' : '给 Monstera 发送消息';
  if (isAgent) loadAgentTasks();
  // Agent 模式的历史对话隐藏由 CSS（.app.mode-agent #histHead/#convList）接管，这里不再折叠
  if (chatAreaEl) syncAgentComposer();   // 切模式后同步输入框位置（空→居中 / 有内容→底部）
  try{ localStorage.setItem('monstera.mode', mode); }catch(_){}
}
$('modeSwitch').addEventListener('click', e => {
  const btn = e.target.closest('.mode-btn');
  if (btn) setMode(btn.dataset.mode);
});
try{ setMode(localStorage.getItem('monstera.mode') === 'agent' ? 'agent' : 'chat'); }
catch(_){ setMode('chat'); }

/* ============================================================
   Phase 4 · Agent 模式 UI 桥接
   原则：UI 层不直接调用内核函数，一律经 HTTP 网关（/api/agent/*）
   与事件（读 tasks/{id}/timeline）交换；历史任务与聊天对话完全分离。
   ============================================================ */
const A = {
  activeTaskId: null,      // 当前正在展示/执行的任务
  running: false,          // 是否有任务正在执行（跑循环中）
  settings: null,          // Phase 5：Agent 设置缓存（硬保护三档 + 两开关）
  es: null,                // Phase 5：当前任务的 SSE 连接（实时进度推送）
};
const TASK_ICONS = {
  completed: `<svg viewBox="0 0 16 16" fill="none"><path d="M3 8.5 6.5 12 13 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  failed: `<svg viewBox="0 0 16 16" fill="none"><path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  executing: `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.8"/><path d="M8 3v5l3.5 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  waiting_human: `<svg viewBox="0 0 16 16" fill="none"><path d="M8 3v5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="8" cy="11.5" r="1.2" fill="currentColor"/></svg>`,
  idle: `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.6"/></svg>`,
};
const TASK_ICON_CLS = { completed:'ok', failed:'err', executing:'run', waiting_human:'wait', idle:'idle' };
function fmtTime(ts){
  if (!ts) return '';
  const d = new Date(ts * 1000);
  const now = Date.now();
  return (now - d.getTime() < 3600e3)
    ? d.toTimeString().slice(0, 5)
    : `${d.getMonth()+1}/${d.getDate()} ${d.toTimeString().slice(0,5)}`;
}
/* Agent 模式空状态：极简引导 + 示例任务（点一下填入输入框，直接回车运行） */
const AGENT_STARTERS = [
  { t:'整理目录', d:'扫描某目录并生成结构说明' },
  { t:'修复代码', d:'排查并修复指定脚本的报错' },
  { t:'写个小工具', d:'新建一个完成某功能的脚本' },
  { t:'批量改文档', d:'对多个文件做统一替换' },
];
function agentEmptyGuide(){
  $('taskView').innerHTML = `
    <div class="agent-guide">
      <div class="ag-h">Agent</div>
      <div class="ag-d">描述你要完成的任务，我会拆解、调用工具执行，并在你确认后落地。默认只有读取/新建是自动的，改动你已有的文件会等你确认。</div>
      <div class="ag-cards">${AGENT_STARTERS.map((s,i)=>`
        <div class="ag-card" data-starter="${i}">
          <div class="agc-t">${s.t}</div>
          <div class="agc-d">${s.d}</div>
        </div>`).join('')}</div>
      <div class="ag-foot">在 Agent 模式下，描述任务 → 回车执行；可随时点停止。</div>
    </div>`;
  syncAgentComposer();
}
/* 输入框位置同步（无内容→中间居中；有内容→下边贴底），两种模式统一规则：
     聊天模式看消息区（#messages）是否真的有消息；
     Agent 模式看任务视图是否在展示真实任务（有 .tv-* 任务结构 → 底部；空态引导/新任务 → 中间），
     避免把"引导卡片文本"误判为有内容。 */
  function syncAgentComposer(){
    const empty = document.querySelector('.app').classList.contains('mode-agent')
      ? !document.querySelector('#taskView .fmsg')
      : !document.getElementById('messages').textContent.trim();
    $('chatArea').classList.toggle('chat--empty', !!empty);
  }
/* —— 中间区：初始化（空状态引导）/ 新任务 —— */
function agentViewInit(){
  agentEmptyGuide();
}
function startNewAgentTask(){
  // Agent 模式「新任务」：清空当前任务视图回引导态，折叠执行面板
  A.activeTaskId = null;
  if (A.es){ A.es.close(); A.es = null; }
  agentEmptyGuide();
  setAgentPane(false);   // 折叠右侧执行面板，避免残留已删任务的陈迹
  loadAgentTasks();
}
/* —— 历史任务折叠区：加载 / 渲染（悬停操作：重试 / 删除） —— */
async function loadAgentTasks(){
  try{
    const rows = await apiFetch('/agent/tasks');
    const list = $('taskList');
    A.taskRows = rows || [];   // 缓存供右键重命名/置顶回填（避免 HTML 转义误差）
    if (!rows || !rows.length){
      list.innerHTML = '<div class="empty-search" style="padding:8px">暂无历史任务</div>';
      return;
    }
    list.innerHTML = rows.map(t => `
      <div class="task-item ${t.taskId === A.activeTaskId ? 'active' : ''}" data-task="${t.taskId}">
        <span class="task-body">
          <span class="task-name">${escHtml(t.title || t.objective)}</span>
          <span class="task-time">${fmtTime(t.completedAt || t.createdAt)} · ${statusLabel(t.status)}</span>
        </span>
        ${t.pinned ? '<span class="conv-pin" title="已置顶">' + PIN_SVG + '</span>' : ''}
        ${t.status === 'failed' ? `<span class="task-ops">
          <button class="task-op retry" data-op="retry" title="从头重试">↻</button>
        </span>` : ''}
      </div>`).join('');
  }catch(err){ /* 静默：列表加载失败不阻塞 */ }
}
function statusLabel(s){
  return ({completed:'成功', failed:'失败', executing:'执行中', waiting_human:'待确认', idle:'待运行'})[s] || s;
}
/* —— 启动任务：创建 + 跑（模型驱动）+ SSE 实时推送 —— */
async function startAgentTask(text){
  if (!text || A.running) return;
  const opt = currentModelOption();
  if (!opt){ toast('暂无可用模型，请先添加 API Key'); return; }
  const created = await apiFetch('/agent/tasks', 'POST', { objective: text });
  A.activeTaskId = created.task_id;
  setAgentPane(true);                       // 自动展开右侧执行面板
  if (window.MonsteraFeed) window.MonsteraFeed(created); // 片3 3-C-b①：启动初始渲染统一喂 store 一次
  agentViewRender(created);                 // 立即渲染初始状态
  loadAgentTasks();
  await runAgentTask(created);
}
/* 执行已创建好的任务（新建/重试共用）：
   SSE 实时推送（/tasks/{id}/stream）为主通道，SSE 不可用时回退 1000ms 轮询。 */
async function runAgentTask(task){
  const opt = currentModelOption();
  if (!opt || A.running) return;
  A.running = true;
  _agentRunning(true);
  try{
    // 后台运行任务（循环阻塞等待用户确认时，前端不依赖 run 响应体，进度由 SSE 推送）
    const p = fetch(API_BASE + `/agent/tasks/${task.task_id}/run`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ model: { provider_id: opt.provider_id, model_id: opt.model_id }, with_gate: true }),
    }).catch(() => {});                       // 失败由快照状态兜底展示
    await streamTask(task.task_id, p);
  }catch(err){
    toast('Agent 任务启动失败：' + err.message);
  }finally{
    A.running = false;
    _agentRunning(false);
    loadAgentTasks();                        // 结束时同步侧栏
  }
}
function _agentRunning(on){
  $('sendBtn').style.display = on ? 'none' : 'flex';
  $('stopBtn').classList.toggle('stopwarn', on);   // 运行态停止按钮红色化
  $('stopBtn').style.display = on ? 'flex' : 'none';
  $('stopBtn').disabled = false;
  $('stopBtn').title = '停止任务';
  $('genHint').hidden = !on;
  $('genHint').textContent = '● 正在执行任务，点击停止';
  if (!on){
    const lv = $('agentRunLine');
    if (lv) lv.classList.remove('show');
    updateSendState();
  }
}
/* —— SSE 主通道：收到快照帧即渲染；终态关闭连接；首帧即失败则回退轮询 —— */
function streamTask(taskId, runP){
  return new Promise(resolve => {
    let gotFrame = false;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      if (A.es){ A.es.close(); A.es = null; }
      resolve();
    };
    const es = new EventSource(API_BASE + `/agent/tasks/${taskId}/stream`);
    A.es = es;
    es.addEventListener('task', ev => {
      let snap;
      try{ snap = JSON.parse(ev.data); }catch(_){ return; }
      gotFrame = true;
      renderTaskSnap(snap);
      const st = snap.status;
      if (st === 'completed' || st === 'failed'){
        toast(st === 'completed' ? '任务已完成' : '任务失败');
        finish();
      }
    });
    es.onerror = () => {
      if (!gotFrame){
        // SSE 完全不可用（旧后端无此端点/代理问题）→ 关闭并回退轮询，保证功能可用
        es.close();
        A.es = null;
        fallbackPoll(taskId, finish);
      }
      // 已连上过：交给 EventSource 自动重连，终态帧最终会到达
    };
  });
}
/* 单帧渲染：中间时间线 + 右侧运行时详情 + 侧栏状态同步 */
function renderTaskSnap(snap){
  if (snap.task_id !== A.activeTaskId && A.activeTaskId) return;   // 守卫：只渲染当前任务
  if (window.MonsteraFeed) window.MonsteraFeed(snap); // 片3 3-C-b①：每帧在此统一喂 store 一次；渲染函数只消费、不再各自写
  agentViewRender(snap);
  agentPaneRender(snap);
  loadAgentTasks();
}
/* —— 兜底轮询：SSE 不可用时的降级通道（1000ms，上限 ~10 分钟） —— */
async function fallbackPoll(taskId, finish){
  for (let i = 0; i < 600; i++){
    try{
      const task = await apiFetch(`/agent/tasks/${taskId}`);
      renderTaskSnap(task);
      const st = task.status;
      if (st === 'completed' || st === 'failed'){
        toast(st === 'completed' ? '任务已完成' : '任务失败');
        finish();
        return;
      }
    }catch(err){ /* 单次轮询失败继续下一次 */ }
    await new Promise(r => setTimeout(r, 1000));
  }
  finish();   // 兜底超时也结束，避免 UI 永远卡在执行态
}
/* —— 中间区：任务时间线渲染（顶部终态横幅 + 纵向步骤流） —— */
function fmtDur(s){
  if (!s || s < 0) return '';
  const m = Math.floor(s / 60), ss = Math.round(s % 60);
  return `${m ? m + '分钟 ' : ''}${ss}秒`;
}
/* —— P2 统一截断原语：N 字截断 + 省略号 + 悬浮完整。
   单一策略：普通详情区一律截断不留全量（证据块=片 8 例外）。
   TRUNC_N=4000 详情/正文；TRUNC_TITLE=60 折叠标题/单行预览。 */
const TRUNC_N = 4000;
const TRUNC_TITLE = 60;
function p2Trunc(s, n){
  const str = String(s == null ? '' : s);
  const full = str;
  const short = str.length > n ? str.slice(0, n) + '…' : str;
  return { short, full };
}
/* —— Codex 式自由消息流：过程消息的摘要标题 + 全文 dump —— */
function fmsgBasename(p){
  const s = String(p || '').replace(/\\/g, '/');
  const seg = s.split('/').filter(Boolean);
  return seg.length ? seg[seg.length - 1] : s;
}
/* 片7 翻译表：裸工具名/失败原因 → 人话（消除确认卡/失败卡/兜底处的内部标识泄漏） */
function fmtToolBase(tool){
  const base = { file_write:'写入文件', file_edit:'编辑文件', file_read:'读取文件', list_dir:'查看目录' }[tool];
  return base || String(tool || '').replace(/_/g, ' ').trim() || '未知操作';
}
function fmtFailReason(r){
  const m = {
    user_stopped: '已被用户中止', user_interrupt: '已被用户中止',
    plan_denied: '计划被拒绝', plan_rejected: '计划被拒绝',
    max_iterations: '已达最大迭代轮数', max_tool_calls: '已达最大工具调用数',
    timeout: '执行超时', step_timeout: '单步超时', error: '执行出错',
  };
  const key = String(r || '').toLowerCase();
  return m[key] || (String(r || '').trim() ? r : '未知原因');
}
/* 定稿三：终止类型统一读取（task.terminate_kind 持久化优先，回退 meta 装饰/默认 error），按全书 B4 四终态出标题。
   三读源（聊天流终态卡 / 执行面板顶部 / 刷新重拉路径）一律走本函数 → 同一次停止三处同文案。 */
function agentTermKind(task){
  if (!task) return 'error';
  if (task.terminate_kind) return task.terminate_kind;
  if (task.meta && task.meta.terminate_kind) return task.meta.terminate_kind;
  return 'error';
}
function agentFailTitle(task){
  const tk = agentTermKind(task);
  if (tk === 'user_interrupt' || tk === 'interrupted') return '任务已被中断';
  if (tk === 'plan_denied') return '计划未执行';
  return '任务执行失败';
}
/* 片7 #3：API 错误人话化——把后端/底层裸错误码映射为陈述句，不让裸 API 错误上屏 */
function humanizeApiErr(d, status){
  const s = String((typeof d === 'string' && d.trim()) ? d : '').toLowerCase();
  if (/invalid.{0,4}api.?key|api.?key.{0,4}invalid|apikey/.test(s)) return 'API Key 无效，请检查后重试';
  if (/unauthorized|invalid_token|401|authentication/.test(s) || s.indexOf('认证') >= 0) return '认证失败，请检查 API Key';
  if (/(insufficient|balance|402)/.test(s) || s.indexOf('余额') >= 0) return '余额不足，请充值后重试';
  if (/(429|rate.?limit|too many|削峰)/.test(s) || s.indexOf('频繁') >= 0 || s.indexOf('限流') >= 0) return '请求过于频繁，请稍后重试';
  if (/404|not found|invalid.?model|unsupported|不存在/.test(s) || s.indexOf('无效的模型') >= 0) return '模型不可用，请检查模型配置';
  if (/(timeout|超时)/.test(s)) return '请求超时，请稍后重试';
  if (/无法连接|no response|unreachable/.test(s) || s.indexOf('未响应') >= 0) return '无法连接后端服务';
  /* 兜底：后端已写人话的（含中文）直接透传；纯英文/内部码一律只陈述状态码，不吐裸 detail 上屏 */
  const hasCjk = /[\u4e00-\u9fff]/.test(String(d || ''));
  return (typeof d === 'string' && d.trim() && hasCjk) ? d : `请求失败（${status || ''}）`;
}
function fmsgToolLabel(tool, args){
  /* 按工具+参数生成自然短语：文件类带文件名，其余回退到语义字段或「调用 <tool>」 */
  const a = args && typeof args === 'object' ? args : {};
  const path = a.path != null ? fmsgBasename(a.path) : null;
  const map = {
    file_write: path ? `写入 ${path}` : '写入文件',
    file_edit:  path ? `编辑 ${path}` : '编辑文件',
    file_read:  path ? `读取 ${path}` : '读取文件',
    list_dir:   path ? `查看目录 ${path}` : '查看目录',
  };
  if (map[tool]) return map[tool];
  if (a.command || a.script) return `运行 ${a.command || a.script}`;
  if (a.query || a.keyword || a.search) return `搜索 ${a.query || a.keyword || a.search}`;
  return `调用 ${fmtToolBase(tool)}`;  /* 片7：兜底不再泄漏裸工具名 */
}
function fmsgDump(data, label){
  /* P2 统一策略：详情区截断(TRUNC_N)+省略号+悬浮完整(title)；原文存 data-full 供「复制」取全文（显示不留全量） */
  const txt = (data === undefined || data === null)
    ? '' : (typeof data === 'string' ? data : JSON.stringify(data, null, 2));
  const { short, full } = p2Trunc(txt, TRUNC_N);
  const trunc = full.length > short.length;
  return `<span class="p2-dump" data-full="${escHtml(full)}"${trunc ? ` title="${escHtml(full)}"` : ''}><span class="extra-head"><em>— ${label} —</em><button class="extra-copy" data-copy-extra>复制</button></span>\n${escHtml(short)}</span>`;
}
function fmsgChipHtml(c, live){
  const flag = c.state === 'err' ? '<span class="fmsg-flag">✕</span>'
             : c.state === 'ok'  ? '<span class="fmsg-flag">✓</span>' : '';
  let detail = '';
  if (c.args != null) detail += fmsgDump(c.args, '参数');
  if (c.result != null) detail += fmsgDump(c.result, '结果');
  if (c.error != null) detail += fmsgDump(c.error, '错误');
  /* data-ext 必须是独立属性（写在 class 引号外），否则会被吞进 class 值 */
  const ext = detail ? ' data-ext="1"' : '';
  /* P2 统一：折叠标题单行截断(TRUNC_TITLE)+悬浮完整(title) */
  const ti = p2Trunc(c.title || '', TRUNC_TITLE);
  const title = ti.short;
  /* 展开决定：执行中(live)强制展开；否则看「用户手动展开集合」fmsgOpenSteps（片 2 折叠保活，活过 SSE 帧） */
  const userOpen = !live && window.MONSTERA_CH && window.MONSTERA_CH.foldPersist !== false && fmsgOpenSteps.has(c.stepNo);
  const cls = `${c.state || ''}${live ? ' live open' : (userOpen ? ' open' : '')}`.trim();
  return `<div class="fmsg-chip ${cls}"${ext} data-step-no="${c.stepNo}">
    <div class="fmsg-chip-h">
      <span class="fmsg-chev">▸</span>${flag}
      <span class="fmsg-chip-t"${ti.full.length > ti.short.length ? ` title="${escHtml(ti.full)}"` : ''}>${escHtml(title)}</span>
    </div>
    ${detail ? `<div class="fmsg-chip-d">${detail}</div>` : ''}
  </div>`;
}
/* 事件流 → 过程消息链（步骤级状态派生，stepStates 语义）：
   - 每个步骤一个 chip（stepNo 为派生的步骤序号——事件本身无 step_id 字段，
     靠 SSE 顺序把 TOOL_CALL/RESULT 挂到最近一次 STEP_STARTED；铁律六：全量重建）。
   - hasCall / hasResult：收到同一步的工具调用/结果标记。判定「执行中」=
     hasCall === true && hasResult === false（OpenHands action_id 配对语义的等价派生）。
   - 工具结果成功/失败来自 TOOL_RESULT_RECEIVED.payload.success（现有字段）；
     用户拒绝工具调用不发 TOOL_RESULT_RECEIVED，只发 OBSERVATION_READY
     （observation.summary 含「用户拒绝」），据此把该步落为失败（拒绝语义）。
   - 目标/意图等仅对模型可见的事件不进入用户消息流。 */
function buildFmsgChips(evs){
  const chips = [];
  let cur = null;
  evs.forEach((e) => {
    if (e.type === 'STEP_STARTED'){
      cur = { stepNo: chips.length + 1, hasCall: false, hasResult: false,
              title: '思考', state: '', args: null, result: null, error: null };
      chips.push(cur);
    }
    else if (e.type === 'TOOL_CALL_REQUESTED'){
      if (!cur || cur.hasResult){
        cur = { stepNo: chips.length + 1, hasCall: false, hasResult: false,
                title: '工具调用', state: '', args: null, result: null, error: null };
        chips.push(cur);
      }
      cur.hasCall = true;
      cur.title = fmsgToolLabel(e.payload.tool, e.payload.args);
      cur.args = e.payload.args;
    }
    else if (e.type === 'TOOL_RESULT_RECEIVED'){
      if (!cur){ cur = { stepNo: chips.length + 1, hasCall: false, hasResult: false,
                         title: '工具调用', state: '', args: null, result: null, error: null }; chips.push(cur); }
      cur.hasResult = true;
      cur.state = e.payload.success ? 'ok' : 'err';
      cur.result = e.payload.success ? e.payload.data : null;
      cur.error = e.payload.success ? null : (e.payload.error || e.payload.data);
      cur = null;   // 该步骤结束
    }
    else if (e.type === 'OBSERVATION_READY'){
      // 用户拒绝工具：无 TOOL_RESULT_RECEIVED，由 OBSERVATION_READY(summary 含「用户拒绝」) 落定该步
      const obs = (e.payload && e.payload.observation) || {};
      if (cur && cur.hasCall && !cur.hasResult && obs.success === false && /用户拒绝/.test(obs.summary || '')){
        cur.hasResult = true;
        cur.state = 'err';
        cur.error = obs.summary;
        cur = null;
      }
    }
  });
  return chips;
}
/* —— 片3 3-C-b②：增量渲染（#taskView only，store 驱动 + Alpine）——
   - 仅在 MONSTERA_CH.render==='incremental' 时被 agentViewRender 调用；默认 legacy，此分支休眠。
   - 首次调用以 Alpine 模板 seed #taskView 根（x-cloak 防闪），随后每次只改 reactive data，Alpine 按 :key 增删改，
     DOM 节点按 stepNo 保活（不整体 innerHTML 重建）。
   - 流式正文（模型最终答案）用 textContent 追加，不碰 Alpine。 */
function renderAgentViewIncremental(v, task){
  const st = task.status || 'idle';
  const running = st === 'executing';
  const done = st === 'completed' || st === 'failed';
  const ok = st === 'completed';

  /* 每 chip 转增量视图对象：stepNo 为稳定 :key；展开决定沿用「执行中强制展开」语义 */
  const chips = buildFmsgChips(task.events || []).map(c => {
    const live = c.hasCall && !c.hasResult;
    let detail = '';
    if (c.args != null) detail += fmsgDump(c.args, '参数');
    if (c.result != null) detail += fmsgDump(c.result, '结果');
    if (c.error != null) detail += fmsgDump(c.error, '错误');
    return {
      stepNo: c.stepNo,
      title: p2Trunc(c.title || '', TRUNC_TITLE).short,
      cls: `${c.state || ''}${live ? ' live open' : ''}`,
      flag: c.state === 'err' ? '✕' : c.state === 'ok' ? '✓' : '',
      detail,
      hasDetail: !!detail,
    };
  });

  const dur = fmtDur((task.completed_at || 0) - (task.created_at || 0));
  const metaLine = `耗时 ${dur || '—'} · 工具 ${task.tool_call_count || 0} 次`;
  let failTitle = agentFailTitle(task); /* 定稿三：统一读取 terminate_kind → 全书 B4 终态文案（含用户停止） */
  const costLine = done
    ? `本次费用 ${task.estimated_cost != null ? '¥' + task.estimated_cost.toFixed(4) : '未知'} · 耗时 ${dur || '—'} · 工具调用 ${task.tool_call_count || 0} 次`
    : '';

  const root = window.MonsteraInkState;
  const taskKey = task.task_id;
  if (root && (v !== root.root || root.taskId !== taskKey)){
    // 视图切换或切任务：整体重 seed，避免 stepNo/chips 跨任务串号
    window.MonsteraInkState = null;
  }
  const cur = window.MonsteraInkState;

  if (!cur){
    const data = window.Alpine.reactive({
      state: st, running, done, ok,
      userText: task.objective || '',
      liveLabel: running ? (agentLiveLabel(task.events || []) || '执行中…') : '',
      chips,
      metaLine, costLine, failTitle, failReason: fmtFailReason(task.fail_reason),
    });
    v.innerHTML = `<div class="fmsg" x-data="monsteraAvData()" x-cloak>
  <div class="fmsg-live" x-show="running" x-text="liveLabel"></div>
  <div class="fmsg-row user">
    <div class="fmsg-bd"><div class="fmsg-user-tx" x-text="userText"></div></div>
    <div class="fmsg-av u">我</div>
  </div>
  <div class="fmsg-row">
    <div class="fmsg-av">M</div>
    <div class="fmsg-bd"><div class="fmsg-col">
      <template x-for="c in chips" :key="c.stepNo">
        <div class="fmsg-chip" :class="c.cls" :data-step-no="c.stepNo" :data-has-detail="c.hasDetail ? '1' : null">
          <div class="fmsg-chip-h">
            <span class="fmsg-chev">▸</span>
            <span class="fmsg-flag" x-show="!!c.flag" x-text="c.flag"></span>
            <span class="fmsg-chip-t" x-text="c.title"></span>
          </div>
          <div class="fmsg-chip-d" x-show="c.hasDetail" x-html="c.detail"></div>
        </div>
      </template>
      <div class="fmsg-text" x-show="ok"><span id="incTvText"></span></div>
      <div class="fmsg-done done" x-show="ok"><span class="fmsg-done-ic">✓</span><div class="fmsg-done-bd"><div class="fmsg-done-t">任务完成</div><div class="fmsg-done-meta" x-text="metaLine"></div></div></div>
      <div class="fmsg-done err" x-show="done && !ok"><span class="fmsg-done-ic">!</span><div class="fmsg-done-bd"><div class="fmsg-done-t" x-text="failTitle"></div><div class="fmsg-done-r" x-text="failReason"></div><div class="fmsg-done-meta" x-text="metaLine"></div></div></div>
      <div class="fmsg-cost-row" x-show="done">
        <span class="fmsg-msg-ops" style="margin-top:0">
          <button class="fmsg-msg-op" data-msg-op="copy-summary" title="复制模型总结">${_MCTX_ICON.copy}</button>
          <button class="fmsg-msg-op" data-msg-op="retry" title="新建同目标任务并自动执行">${_MCTX_ICON.regen}</button>
        </span>
        <span class="fmsg-cost" x-text="costLine"></span>
      </div>
    </div></div>
  </div>
</div>`;
    window.monsteraAvData = function () { return data; };
    window.Alpine.initTree(v);
    window.MonsteraInkState = { root: v, data, taskId: taskKey };
  } else {
    const d = cur.data;
    d.state = st; d.running = running; d.done = done; d.ok = ok;
    d.userText = task.objective || '';
    d.liveLabel = running ? (agentLiveLabel(task.events || []) || '执行中…') : '';
    d.chips = chips;
    d.metaLine = metaLine; d.costLine = costLine; d.failTitle = failTitle;
    d.failReason = fmtFailReason(task.fail_reason);
  }
  /* 流式正文：textContent 追加，不碰 Alpine */
  if (ok){
    const m = (cur || window.MonsteraInkState).root.querySelector('#incTvText');
    if (m && task.final_answer != null) m.textContent = String(task.final_answer);
  }
  /* 片 1 P4：中间时间线滚动主权不回归 */
  ensureAgentScrollRegion(v);
  if (window.MONSTERA_CH && window.MONSTERA_CH.agentScroll !== false){
    maybeAutoScroll(v);
    requestAnimationFrame(() => { maybeAutoScroll(v); });
  } else {
    v.scrollTop = v.scrollHeight;
    requestAnimationFrame(() => { v.scrollTop = v.scrollHeight; });
  }
}
function agentViewRender(task){
  const v = $('taskView');
  if (!task) return;
  /* 片3 3-C-b②：增量渲染分支（#taskView only）。仅在 MONSTERA_CH.render==='incremental' 时走 store 驱动 + Alpine
     x-for(带 :key)。默认 legacy（ch10.js 顶部默认值），此分支休眠，不切默认。 */
  if (window.Alpine && window.MONSTERA_CH && window.MONSTERA_CH.render === 'incremental'){
    renderAgentViewIncremental(v, task);
    syncAgentComposer(); // 片3 3-C-b-fix：镜像 legacy 路径，渲染后复位 chat--empty，确保 #taskView 可见（否则 display:none）
    return;
  }
  syncAgentComposer();
  const st = task.status || 'idle';
  const evs = task.events || [];
  const running = st === 'executing';

  /* —— 用户消息：靠右 + 右侧头像（每次发任务显示一次）；终态下方浮现复制/删除本轮图标 —— */
  const done = st === 'completed' || st === 'failed';
  const userRow = `<div class="fmsg-row user">
    <div class="fmsg-bd">
      <div class="fmsg-user-tx">${escHtml(task.objective || '')}</div>
      ${done ? `<div class="fmsg-msg-ops">
        <button class="fmsg-msg-op" data-msg-op="copy" title="复制用户消息">${_MCTX_ICON.copy}</button>
        <button class="fmsg-msg-op danger" data-msg-op="del" title="删除本轮全部对话">${_MCTX_ICON.del}</button>
      </div>` : ''}
    </div>
    <div class="fmsg-av u">我</div>
  </div>`;

  /* —— 等待用户确认/计划确认：内联到对话流（Codex Approval 卡语义，从右侧面板搬入中间）—— */
  const human = [...evs].reverse().find(e => e.type === 'HUMAN_INTERVENTION_REQUIRED');
  let confirm = '';
  if (st === 'waiting_human' && human){
    const p = human.payload;
    const isPlan = p.level === 'plan_confirm';
    confirm = `<div class="agent-confirm" id="agentConfirm">
      <div class="agent-confirm-t">${isPlan ? '📋 计划确认' : '⚠ 危险操作 · 等待你确认'}</div>
      <div class="agent-confirm-d">${isPlan ? escHtml(p.reason) : `工具：<b>${escHtml(fmtToolBase(p.tool))}</b><br>${escHtml(p.reason)}`}</div>
      <div class="agent-confirm-btns">
        <button class="agent-btn allow" data-act="allow">${isPlan ? '开始执行' : '允许'}</button>
        <button class="agent-btn deny" data-act="deny">${isPlan ? '取消' : '拒绝'}</button>
      </div>
    </div>`;
  }

  /* —— 过程消息链（小字号淡字）：步骤级判定：
       ① hasCall=true && hasResult=false → 执行中，强制展开
       ② hasResult=true → 已结束，默认折叠
       （指令一要求：用 stepStates 语义，不再按 liveIdx 单最后一条，执行中步骤一律展开） */
  const chips = buildFmsgChips(evs);
  /* 片 2 折叠保活：重建前捕获当前用户展开步（open 且非 live），并剪除已不存在的 stepNo。
     串任务隔离：task_id 变化时【不携带旧任务的展开步】——先清空、跳过本次捕获，
     让新任务从默认全折叠起步，避免 stepNo 跨任务泄漏。 */
  if (window.MONSTERA_CH && window.MONSTERA_CH.foldPersist !== false){
    if (fmsgOpenForTaskId !== task.task_id){
      fmsgOpenSteps.clear();
      fmsgOpenForTaskId = task.task_id;
    } else {
      v.querySelectorAll('.fmsg-chip.open:not(.live)').forEach(el => {
        const n = parseInt(el.dataset.stepNo, 10);
        if (Number.isInteger(n)) fmsgOpenSteps.add(n);
      });
      const alive = new Set(chips.map(c => c.stepNo));
      fmsgOpenSteps.forEach(n => { if (!alive.has(n)) fmsgOpenSteps.delete(n); });
    }
  }
  const chipsHtml = chips.map((c) => fmsgChipHtml(c, c.hasCall && !c.hasResult)).join('');

  /* —— 模型自然文字（正常字号、正文直接呈现）—— */
  let textHtml = '';
  if (st === 'completed' && (task.final_answer || '').toString().trim()){
    textHtml = `<div class="fmsg-text">${escHtml(task.final_answer.toString().trim())}</div>`;
  }

  /* —— 完成/失败卡片（轻量、视觉比正文稍突出）+ 费用行（真实调用过模型才显示）——
     失败终态按快照层装饰的 meta.terminate_kind 区分文案：user_interrupt / plan_denied / error */
  let doneHtml = '', costHtml = '';
  if (st === 'completed' || st === 'failed'){
    const ok = st === 'completed';
    const dur = fmtDur((task.completed_at || 0) - (task.created_at || 0));
    const meta = `耗时 ${dur || '—'} · 工具 ${task.tool_call_count || 0} 次`;
    let failTitle = agentFailTitle(task); /* 定稿三：统一读取 terminate_kind → 全书 B4 终态文案 */
    doneHtml = ok
      ? `<div class="fmsg-done done"><span class="fmsg-done-ic">✓</span>
          <div class="fmsg-done-bd">
            <div class="fmsg-done-t">任务完成</div>
            <div class="fmsg-done-meta">${meta}</div>
          </div></div>`
      : `<div class="fmsg-done err"><span class="fmsg-done-ic">!</span>
          <div class="fmsg-done-bd">
            <div class="fmsg-done-t">${failTitle}</div>
            <div class="fmsg-done-r">${escHtml(fmtFailReason(task.fail_reason))}</div>
            <div class="fmsg-done-meta">${meta}</div>
          </div></div>`;
    // 费用行：左侧图标（复制模型总结 / 从头重试）+ 弱化小字费用，只在终态出现
    costHtml = `<div class="fmsg-cost-row">
      <span class="fmsg-msg-ops" style="margin-top:0">
        <button class="fmsg-msg-op" data-msg-op="copy-summary" title="复制模型总结">${_MCTX_ICON.copy}</button>
        <button class="fmsg-msg-op" data-msg-op="retry" title="新建同目标任务并自动执行" ${A.running ? 'disabled' : ''}>${_MCTX_ICON.regen}</button>
      </span>
      <span class="fmsg-cost">本次费用 ${task.estimated_cost != null ? '¥' + task.estimated_cost.toFixed(4) : '未知'} · 耗时 ${dur || '—'} · 工具调用 ${task.tool_call_count || 0} 次</span>
    </div>`;
  }

  /* —— 运行中：消息流顶部 sticky「当前动作」（OpenHands/Codex live chip 语义）—— */
  let liveHtml = '';
  if (running) liveHtml = `<div class="fmsg-live">${agentLiveLabel(evs) || '执行中…'}</div>`;

  v.innerHTML = `<div class="fmsg">
    ${liveHtml}
    ${userRow}
    <div class="fmsg-row">
      <div class="fmsg-av">M</div>
      <div class="fmsg-bd"><div class="fmsg-col">
        ${confirm}
        ${chipsHtml}
        ${textHtml}
        ${doneHtml}
        ${costHtml}
      </div></div>
    </div>
  </div>`;
  ensureAgentScrollRegion(v);   // 片 1 P4：中间区回底按钮重挂 + 滚动绑定（首次生效）
  if (window.MONSTERA_CH && window.MONSTERA_CH.agentScroll !== false){
    maybeAutoScroll(v);   // Agent 中间时间线：仅贴底时跟随；用户上翻不再被拉回（片 1 P4）
    requestAnimationFrame(() => { maybeAutoScroll(v); });  // 布局刷新后再判，确保打开历史长任务时底部完成卡可见
  } else {
    v.scrollTop = v.scrollHeight;
    requestAnimationFrame(() => { v.scrollTop = v.scrollHeight; });
  }
  syncAgentComposer();   // 渲染完成后按最新内容复位输入框位置（有任务→底部 / 空态→中间）
}
/* —— 右侧执行面板 · 运行时详情：事件流 + 确认卡 + 成本摘要 —— */
function paneEventRow(e){
  const p = e.payload || {};
  switch (e.type){
    case 'INTENT_RECEIVED':
      return paneRowHtml('gold', '◎', '已接收目标', escHtml(p2Trunc(p.objective || '', 70).short), '', '');
    default:
      return '';
  }
}
function paneDetail(data, label){
  /* P2 统一策略：详情区截断(TRUNC_N)+省略号+悬浮完整(title)；原文存 data-full 供「复制」取全文 */
  if (data === undefined || data === null) return '';
  const txt = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  const { short, full } = p2Trunc(txt, TRUNC_N);
  const trunc = full.length > short.length;
  return `<span class="pane-row-extra p2-dump" data-full="${escHtml(full)}"${trunc ? ` title="${escHtml(full)}"` : ''}><span class="extra-head"><em>— ${label} —</em><button class="extra-copy" data-copy-extra>复制</button></span>\n${escHtml(short)}</span>`;
}
function paneRowHtml(cls, ic, title, desc, extra, time){
  // Phase 6 UI 极简：行尾不再内联显示时间，改为行悬停提示（减少每行视觉噪声）
  return `<div class="pane-row"${extra ? ' data-ext="1"' : ''}${time ? ` title="${time}"` : ''}>
    <span class="pane-ic ${cls}">${ic}</span>
    <span class="pane-row-body">
      <span class="pane-row-head"><span class="pane-row-t">${title}</span></span>
      ${desc ? `<span class="pane-row-desc">${desc}</span>` : ''}
      ${extra || ''}
    </span>
  </div>`;
}
/* 右侧面板·交互重构：把扁平事件流按「步骤」分组为追踪块（阶段词 chip + 工具 + 徽章 + 展开） */
/* 片8 C3 证据块：每轮(步)从 TOOL_RESULT_RECEIVED 真实字段渲染证据行（文件证据为主，结论/命令数据门控）。
   P1 折叠保活：paneEvOpenSteps 键 stepNo 持久化，pane 每帧重建不丢展开态。
   P2 截断：详情走 paneDetail；file_edit/file_write 无 diff 字段 → 按红线1只渲染真实 summary/字节，不伪造 diff。 */
const paneEvOpenSteps = new Set();
function paneEvToggle(stepNo, open){ if (open) paneEvOpenSteps.add(stepNo); else paneEvOpenSteps.delete(stepNo); }
function buildEvidence(s){
  if (!(window.MONSTERA_CH && window.MONSTERA_CH.evidenceBlocks)) return '';
  const tool = s.evTool; if (!tool) return '';
  const succ = !!s.evSucc;
  const d = (s.evData && typeof s.evData === 'object') ? s.evData : {};
  const fn = fmsgBasename(d.path);
  const open = paneEvOpenSteps.has(s.no);
  const label = fn ? fmsgToolLabel(tool, { path: d.path }) : fmtToolBase(tool);
  const stDot = succ ? '<span class="ev-status ok">✓</span>' : '<span class="ev-status err">✗</span>';
  const isFile = /^file_|^list_dir/.test(tool);
  let detail = '';
  if (tool === 'file_read') detail = paneDetail(d.content, '内容');
  else if (tool === 'file_write') detail = `<div class="ev-detail">${escHtml(d.mode === 'created' ? '新建文件' : '覆盖已有文件')} · ${d.bytes ?? ''} 字节</div>`;
  else if (tool === 'file_edit') detail = `<div class="ev-detail">${escHtml(d.summary || '已修改')} · ${d.bytes ?? ''} 字节</div>`;
  else if (tool === 'list_dir'){ const names = (d.entries || []).slice(0, 60).map(x => x.name).join(' · '); detail = `<div class="ev-detail">${d.count ?? 0} 项：${escHtml(names)}</div>`; }
  else if (d.summary) detail = `<div class="ev-detail">${escHtml(d.summary)}</div>`;
  else if (!succ) detail = `<div class="ev-detail">失败：${escHtml(String(s.evError || ''))}</div>`;
  else detail = paneDetail(d, '结果');
  return `<div class="pane-evidence">
    <div class="ev-row${open ? ' open' : ''}" data-ev data-step="${s.no}" title="${escHtml(label)}">
      <span class="ev-chev">${open ? '▾' : '▸'}</span>
      <span class="ev-ic">${isFile ? '◇' : '·'}</span>
      <span class="ev-label">${escHtml(label)}</span>${stDot}
    </div>
    <div class="ev-detail-wrap">${detail}</div>
  </div>`;
}
function paneSteps(evs, running){
  const steps = [];
  let stepNo = 0;
  evs.forEach((e) => {
    if (e.type === 'STEP_STARTED'){
      stepNo++; steps.push({no: stepNo, state:'', phase:'think', phaseTxt:'思考', tool:'', rslt:'', extra:'', hasDetail:false});
    }
    else if (e.type === 'TOOL_CALL_REQUESTED' && steps.length){
      const last = steps[steps.length - 1];
      last.phase = 'tool'; last.phaseTxt = '调用工具'; last.tool = escHtml(e.payload.tool); last.toolRaw = e.payload.tool;
      last.extra += paneDetail(e.payload.args, '参数'); last.hasDetail = true;
    }
    else if (e.type === 'TOOL_RESULT_RECEIVED' && steps.length){
      const last = steps[steps.length - 1];
      last.state = e.payload.success ? 'ok' : 'err';
      last.phase = e.payload.success ? 'ok' : 'err';
      last.phaseTxt = e.payload.success ? '工具完成' : '工具失败';
      const d = e.payload.data;
      const txt = (typeof d === 'object' ? JSON.stringify(d) : String(d ?? ''));
      last.rslt = escHtml(p2Trunc(txt, 100).short);
      last.extra += paneDetail(e.payload.success ? e.payload.data : { error: e.payload.error || e.payload.data },
        e.payload.success ? '结果' : '错误');
      last.hasDetail = true;
      /* 片8 C3：记录真实结果字段供证据块渲染（不伪造 diff） */
      last.evTool = e.payload.tool || last.toolRaw; last.evSucc = !!e.payload.success;
      last.evData = e.payload.data; last.evError = e.payload.error;
    }
    else if (e.type === 'HUMAN_INTERVENTION_REQUIRED'){
      const p = e.payload; const isPlan = p.level === 'plan_confirm';
      steps.push({no:'!', state:'wait', phase:'wait',
        phaseTxt: isPlan ? '计划确认' : '等待确认',
        tool: isPlan ? '' : escHtml(p.tool),
        rslt: escHtml(p2Trunc(p.reason || '', 100).short),
        extra: paneDetail(p, '确认详情'), hasDetail:true});
    }
  });
  const runIdx = running ? steps.length - 1 : -1;
  /* Phase 6 对标 dsh/Codex：每轮(Turn)一个可折叠组——折叠时一行摘要「第N轮 · 思考/工具×M」，
     默认折叠历史轮、展开当前执行轮；组内保留紧凑单行轨迹（▹ 调用 → ✓/✗ 完成）。 */
  return steps.map((s, i) => {
    const exp = i === runIdx;                                  // 运行中：当前轮自动展开
    const cls = s.state === 'ok' ? 'ok' : s.state === 'err' ? 'err' : (s.state === 'wait' ? 'wait' : (s.phase === 'tool' ? 'gold' : ''));
    const gly = s.state === 'ok' ? '✓' : s.state === 'err' ? '✗' : (s.state === 'wait' ? '?' : (s.phase === 'tool' ? '▹' : '·'));
    let label;
    if (s.state === 'ok') label = `工具完成 <em>${s.tool}</em>`;
    else if (s.state === 'err') label = `工具失败 <em>${s.tool}</em>`;
    else if (s.phase === 'tool') label = `调用工具 <em>${s.tool}</em>`;
    else if (s.state === 'wait') label = s.phaseTxt;
    else label = '思考中…';
    const prevTxt = s.tool ? `→ ${s.tool}${s.rslt ? ' · ' + s.rslt : ''}` : s.phaseTxt;
    const inner = `<div class="pane-row ${cls}${s.hasDetail ? ' data-ext="1"' : ''}${i === runIdx ? ' live' : ''}">
      <span class="pane-ic ${cls}">${gly}</span>
      <span class="pane-row-body">
        <span class="pane-row-head"><span class="pane-row-t">${label}</span></span>
        ${s.rslt ? `<span class="pane-row-desc">${s.rslt}</span>` : ''}
        ${s.hasDetail ? `<span class="pane-row-extra">${s.extra}</span>` : ''}
      </span>
    </div>`;
    return `<div class="pane-turn ${exp ? 'exp' : ''}${i === runIdx ? ' live' : ''}" data-turn="${s.no}">
      <div class="pane-turn-head">
        <span class="pane-turn-chev">▸</span>
        <span class="pane-turn-t">第${s.no}轮</span>
        <span class="pane-turn-prev">${prevTxt}</span>
        ${running && i === runIdx ? '<span class="pane-turn-phase">执行中</span>' : ''}
      </div>
      <div class="pane-turn-body">${inner}${(window.MONSTERA_CH && window.MONSTERA_CH.evidenceBlocks) ? buildEvidence(s) : ''}</div>
    </div>`;
  }).join('');
}
/* 当前"正在做什么"的短标签（由 stepStates 活跃步派生，非本地维护状态）：
   扫描 chips，取最近一个 hasCall===true && hasResult===false 的步骤 → 读取其工具名/动作生成文案；
   无活跃步骤且任务未终态时返回空串（由调用方给兜底文案）。 */
function agentLiveLabel(evs){
  const chips = buildFmsgChips(evs || []);
  for (let i = chips.length - 1; i >= 0; i--){
    const s = chips[i];
    if (s.hasCall && !s.hasResult) return `正在 ${s.title}`;
  }
  return '';
}
function agentPaneRender(task){
  const body = $('agentBody');
  if (!task) return;
  const st = task.status || 'idle';
  const evs = task.events || [];
  const done = st === 'completed' || st === 'failed';
  const running = st === 'executing';

  // 顶部固定计量条（对齐 dsh 右栏计量面板语义）：步数/工具/耗时/tokens/费用，不随轨迹滚动
  const mu = task.model_usage || {};
  const dur = fmtDur((task.completed_at || 0) - (task.created_at || 0));
  const meter = [];
  meter.push(`步数 ${task.loop_iterations || 0}`);
  meter.push(`工具 ${task.tool_call_count || 0}`);
  meter.push(`耗时 ${dur || '—'}`);
  if (mu.prompt_tokens) meter.push(`tokens ${fmtToken(mu.prompt_tokens)}/${fmtToken(mu.completion_tokens || 0)}`);
  if (task.estimated_cost != null) meter.push(`费用 ¥${task.estimated_cost.toFixed(4)}`);

  const intent = evs.find(e => e.type === 'INTENT_RECEIVED');
  const lead = intent ? paneEventRow(intent) : '';
  const blocks = paneSteps(evs, running);

  let footer = '';
  if (done){
    if (st === 'failed'){
      footer = `<button class="agent-retry" id="agentRetry" ${A.running ? 'disabled' : ''}>↻ 从头重试（新建同目标任务）</button>`;
    }
  } else if (running || st === 'idle'){
    footer = `<div class="agent-running">${running ? '执行中，步骤实时更新…' : '任务待运行'}</div>`;
  }

  body.innerHTML = `
    <div class="agent-pane-head">
      <span class="agent-pane-title">${escHtml(task.objective || '')}</span>
      <span class="agent-pane-status ${running ? 'run pulse' : ''}">${st === 'failed' ? agentFailTitle(task) : statusLabel(st)}</span>
    </div>
    <div class="agent-pane-meter">${meter.join('')}</div>
    <div class="agent-pane-stream">${lead}${blocks ? '<div class="pane-turnbar"><button id="paneUnfoldAll" title="展开全部轮次">全部展开</button><button id="paneFoldAll" title="折叠全部轮次">全部折叠</button></div>' + blocks : '<div class="pane-empty">等待执行事件…</div>'}</div>
    ${footer}`;
  const stream = body.querySelector('.agent-pane-stream');
  if (stream){
    ensureAgentScrollRegion(stream);   // 片 1 P4：面板流每次重建后重挂按钮 + 重新绑定
    if (window.MONSTERA_CH && window.MONSTERA_CH.agentScroll !== false){
      maybeAutoScroll(stream);   // 右侧面板滚动主权：仅贴底时跟随（片 1 P4）
    } else {
      stream.scrollTop = stream.scrollHeight;
    }
  }

  // 同步 composer 的实时活动行：运行中显示"正在做什么"，结束即隐藏
  const lv = $('agentRunLine');
  if (lv){
    const txt = $('agentRunText');
    if (running){
      const label = agentLiveLabel(evs);
      lv.classList.add('show');
      if (txt) txt.innerHTML = label || '执行中…';
    } else {
      lv.classList.remove('show');
    }
  }
}
/* 片8 I1/I2 互定位（门控 mutualLocate）：目标入视口居中 + 一档背景差闪烁一次 .3s（全书唯一引导性动效）。
   定位=用户显式新意图：用 scrollIntoView（不经 maybeAutoScroll），故 P4 滚动锁 up 保持不变，后续 SSE 帧不拉回。 */
function locateFlash(el){
  if (!el) return;
  el.scrollIntoView({ block: 'center', behavior: 'auto' });
  el.classList.add('locate');
  setTimeout(() => el.classList.remove('locate'), 300);
}
function locateChatToTurn(no){
  if (!(window.MONSTERA_CH && window.MONSTERA_CH.mutualLocate)) return;
  if (no == null) return;
  const chip = document.querySelector(`#taskView .fmsg-chip[data-step-no="${no}"]`);
  if (chip) locateFlash(chip);
}
function locatePaneToTurn(no){
  if (!(window.MONSTERA_CH && window.MONSTERA_CH.mutualLocate)) return;
  if (no == null) return;
  const turn = document.querySelector(`#agentBody .pane-turn[data-turn="${no}"]`);
  if (turn) locateFlash(turn);
}
/* 确认/拒绝/横幅操作/重试：委托到任务视图与右侧面板 */
function bindAgentDecision(){
  const v = $('taskView'), body = $('agentBody');
  [v, body].forEach(container => {
    container.addEventListener('click', e => {
      // 空状态示例任务：点击填入输入框并聚焦（Agent 模式引导）
      const starter = e.target.closest('.ag-card[data-starter]');
      if (starter && !A.running){
        const s = AGENT_STARTERS[+starter.dataset.starter];
        if (s){ inputEl.value = s.t + '：'; inputEl.focus(); autoResize(); }
        return;
      }
      // Phase 6：轮次组折叠切换 + 全部展开/全部折叠
      const turnHead = e.target.closest('.pane-turn-head');
      if (turnHead){
        turnHead.parentElement.classList.toggle('exp');
        // 片8 I2：C→B 定位——点轮次头定位聊天流对应消息（门控 mutualLocate；scrollIntoView 不重置 P4 滚动锁）
        if (window.MONSTERA_CH && window.MONSTERA_CH.mutualLocate){
          const turnNo = parseInt(turnHead.parentElement.dataset.turn, 10);
          if (Number.isInteger(turnNo)) locateChatToTurn(turnNo);
        }
        return;
      }
      // 片8 C3：证据行折叠切换（P1 保活，键 stepNo 持久化，pane 每帧重建不丢展开态）
      const evRow = e.target.closest('.ev-row[data-ev]');
      if (evRow){
        const willOpen = !evRow.classList.contains('open');
        evRow.classList.toggle('open', willOpen);
        const stepNo = parseInt(evRow.dataset.step, 10);
        if (Number.isInteger(stepNo)) paneEvToggle(stepNo, willOpen);
        const chev = evRow.querySelector('.ev-chev'); if (chev) chev.textContent = willOpen ? '▾' : '▸';
        return;
      }
      if (e.target.closest('#paneUnfoldAll')){
        container.querySelectorAll('.pane-turn').forEach(t => t.classList.add('exp'));
        return;
      }
      if (e.target.closest('#paneFoldAll')){
        container.querySelectorAll('.pane-turn').forEach(t => t.classList.remove('exp'));
        return;
      }
      // Codex 式消息流：点击过程消息行 → 展开/收起全文（当前执行中自动展开，其余默认折叠）
      const cex = e.target.closest('[data-copy-extra]');
      if (cex){
        // 复制详情块数据（不含「— 标签 —」与按钮本身）；须在 chip 展开分支之前，避免误触展开
        e.stopPropagation();
        const head = cex.closest('.extra-head');
        const box = head && head.parentElement;
        if (!box) return;
        // P2 统一：详情块带 data-full（原文）时优先复制全文，否则退回复制渲染文本（避免截断后丢失原文）
        const full = box.getAttribute('data-full');
        let text;
        if (full != null) text = full;
        else { const clone = box.cloneNode(true); clone.querySelectorAll('.extra-head').forEach(h => h.remove()); text = (clone.textContent || '').trim(); }
        navigator.clipboard.writeText(text).then(
          () => toast('已复制'), () => toast('复制失败，请手动复制'));
        return;
      }
      const chip = e.target.closest('.fmsg-chip[data-ext]');
      if (chip){
        const willOpen = !chip.classList.contains('open');
        chip.classList.toggle('open', willOpen);
        /* 片 2 折叠保活：同步用户展开集合（live 步强制展开、不参与持久化，跳过） */
        if (window.MONSTERA_CH && window.MONSTERA_CH.foldPersist !== false && !chip.classList.contains('live')){
          const n = parseInt(chip.dataset.stepNo, 10);
          if (Number.isInteger(n)){
            if (willOpen) fmsgOpenSteps.add(n); else fmsgOpenSteps.delete(n);
          }
        }
        // 片8 I1：B→C 定位——点聊天 chip 定位执行面板对应轮次（门控 mutualLocate；不重置 P4 滚动锁）
        if (window.MONSTERA_CH && window.MONSTERA_CH.mutualLocate){
          const step = parseInt(chip.dataset.stepNo, 10);
          if (Number.isInteger(step)) locatePaneToTurn(step);
        }
        return;
      }
      const btn = e.target.closest('.agent-btn[data-act]');
      if (btn){
        const act = btn.dataset.act;
        if (A.activeTaskId){
          btn.disabled = true;
          apiFetch(`/agent/tasks/${A.activeTaskId}/decision`, 'POST', {
            allow: act === 'allow',
            reason: act === 'deny' ? '用户在 UI 上拒绝了该操作' : '',
          }).then(() => {
            toast(act === 'allow' ? '已允许，继续执行' : '已拒绝，Agent 将重新决策');
            A.confirmLock = null;
          }).catch(err => { toast('确认失败：' + err.message); btn.disabled = false; });
        }
        return;
      }
      // 右侧执行面板的失败重试（保留，面板不动）
      if (e.target.closest('#agentRetry') && A.activeTaskId){
        retryAgentTask(A.activeTaskId);
        return;
      }
      // 终态消息流操作（图标）：复制用户消息 / 删除本轮 / 复制模型总结 / 从头重试
      const mop = e.target.closest('[data-msg-op]');
      if (mop && A.activeTaskId){
        const op = mop.dataset.msgOp;
        if (op === 'copy'){
          const row = mop.closest('.fmsg-row.user');
          const tx = row && row.querySelector('.fmsg-user-tx');
          const text = tx ? tx.textContent.trim() : '';
          if (text) navigator.clipboard.writeText(text).then(() => toast('已复制'), () => toast('复制失败'));
          else toast('暂无可复制的内容');
        } else if (op === 'del'){
          deleteAgentTask(A.activeTaskId, mop);
        } else if (op === 'copy-summary'){
          copyTaskSummary(A.activeTaskId);
        } else if (op === 'retry'){
          retryAgentTask(A.activeTaskId);
        }
        return;
      }
    });
  });
}
/* 复制任务最终总结（完成时） */
function copyTaskSummary(taskId){
  apiFetch(`/agent/tasks/${taskId}`).then(t => {
    const text = t.final_answer || t.objective || '';
    if (!text) { toast('该任务没有可复制的总结'); return; }
    (navigator.clipboard ? navigator.clipboard.writeText(String(text)) : Promise.reject())
      .then(() => toast('已复制总结'))
      .catch(() => { prompt('复制失败，请手动复制：', String(text).slice(0, 4000)); });
  }).catch(err => toast('获取任务失败：' + err.message));
}
/* 删除任务（终态）：直接删除 + 清视图回引导态（本地数据，操作即生效） */
async function deleteAgentTask(taskId, btnEl){
  if (!taskId) return;
  if (btnEl){ btnEl.disabled = true; }
  try{
    await apiFetch(`/agent/tasks/${taskId}`, 'DELETE');
    toast('任务已删除');
    if (A.activeTaskId === taskId){
      startNewAgentTask();
    } else {
      loadAgentTasks();
    }
  }catch(err){
    toast('删除失败：' + err.message);
    if (btnEl){ btnEl.disabled = false; }
  }
}
/* Phase 5：错误恢复（从头重试）——失败任务 → 新建同目标任务并自动执行 */
async function retryAgentTask(oldId){
  if (A.running) return;
  try{
    const res = await apiFetch(`/agent/tasks/${oldId}/retry`, 'POST');
    const task = res.task;
    A.activeTaskId = task.task_id;
    setAgentPane(true);
    if (window.MonsteraFeed) window.MonsteraFeed(task); // 片3 3-C-b①：重试任务统一喂 store 一次
    agentViewRender(task);                 // 立即切换到新任务视图
    loadAgentTasks();
    toast('已创建重试任务，开始执行');
    await runAgentTask(task);
  }catch(err){ toast('从头重试失败：' + err.message); }
}
/* —— Phase 5：设置面板（硬保护三档 + 两开关） —— */
/* 加载：GET /agent/settings → 填充面板 */
async function loadAgentSettings(){
  try{
    A.settings = await apiFetch('/agent/settings');
    if (A.settings){
      $('setMaxIter').value = A.settings.max_iterations;
      $('setMaxCalls').value = A.settings.max_tool_calls;
      $('setStepTimeout').value = A.settings.step_timeout_s;
      setSwitch('setPlanConfirm', !!A.settings.plan_confirm);
      setSwitch('setAutoOverwrite', !!A.settings.auto_allow_overwrite);
    }
  }catch(err){ /* 静默：设置加载失败用默认控件值 */ }
}
/* 开关控件辅助：.on 切换 + 状态 */
function setSwitch(id, on){ $(id).classList.toggle('on', on); }
function switchOn(id){ return $(id).classList.contains('on'); }
/* 保存：PUT /agent/settings（部分更新，数值由后端钳制后回填） */
async function saveAgentSettings(){
  const patch = {
    max_iterations: parseInt($('setMaxIter').value, 10) || 50,
    max_tool_calls: parseInt($('setMaxCalls').value, 10) || 30,
    step_timeout_s: parseFloat($('setStepTimeout').value) || 60,
    plan_confirm: switchOn('setPlanConfirm'),
    auto_allow_overwrite: switchOn('setAutoOverwrite'),
  };
  const saveBtn = $('agentSetSave');
  saveBtn.disabled = true;
  try{
    A.settings = await apiFetch('/agent/settings', 'PUT', patch);
    // 后端钳制后的真实值回填
    $('setMaxIter').value = A.settings.max_iterations;
    $('setMaxCalls').value = A.settings.max_tool_calls;
    $('setStepTimeout').value = A.settings.step_timeout_s;
    toast('设置已保存');
  }catch(err){
    toast('设置保存失败：' + err.message);
  }finally{
    saveBtn.disabled = false;
  }
}
/* 设置面板开合 */
function bindAgentSettings(){
  const btn = $('agentSetBtn'), panel = $('agentSettings');
  btn.addEventListener('click', () => {
    const open = panel.hidden;
    panel.hidden = !open;
    btn.classList.toggle('open', !!open);
  });
  $('setPlanConfirm').addEventListener('click', () => setSwitch('setPlanConfirm', !switchOn('setPlanConfirm')));
  $('setAutoOverwrite').addEventListener('click', () => setSwitch('setAutoOverwrite', !switchOn('setAutoOverwrite')));
  $('agentSetSave').addEventListener('click', saveAgentSettings);
  loadAgentSettings();
}
/* 历史任务点击：加载该任务完整时间线；悬浮按钮（重试/删除）单独处理 */
function bindTaskList(){
  $('taskList').addEventListener('click', e => {
    const item = e.target.closest('.task-item[data-task]');
    if (!item) return;
    /* 悬浮操作按钮：不冒泡到加载任务 */
    const op = e.target.closest('.task-op');
    if (op){
      e.stopPropagation();
      if (op.dataset.op === 'retry'){
        retryAgentTask(item.dataset.task);
      } else if (op.dataset.op === 'del'){
        deleteAgentTask(item.dataset.task, op);
      }
      return;
    }
    A.activeTaskId = item.dataset.task;
    apiFetch(`/agent/tasks/${A.activeTaskId}`).then(task => {
      if (window.MonsteraFeed) window.MonsteraFeed(task); // 片3 3-C-b①：历史任务加载统一喂 store 一次
      agentViewRender(task);
      agentPaneRender(task);
      loadAgentTasks();
      setAgentPane(true);
    }).catch(err => toast('加载任务失败：' + err.message));
  });
}
/* 历史任务折叠 */
$('agentHistToggle').addEventListener('click', () => sidebarEl.classList.toggle('agent-hist-collapsed'));
function initAgentUI(){
  agentViewInit();
  bindAgentDecision();
  bindTaskList();
  bindAgentSettings();                       // Phase 5：设置面板
  try{ if (localStorage.getItem('monstera.mode') === 'agent') loadAgentTasks(); }catch(_){}
}
initAgentUI();

/* ---------- 左侧栏整体折叠（默认展开）——由左上角标题栏折叠钮控制 ---------- */
$('wcSideBar').addEventListener('click', () => {
  appEl.classList.toggle('side-hidden');
  try{ localStorage.setItem('monstera.sideHidden', appEl.classList.contains('side-hidden') ? '1' : ''); }catch(_){}
});
// 连点折叠钮时阻止冒泡到标题栏的 maximize 逻辑
$('wcSideBar').addEventListener('dblclick', e => e.stopPropagation());
try{ if (localStorage.getItem('monstera.sideHidden') === '1') appEl.classList.add('side-hidden'); }catch(_){}

/* ---------- 历史对话折叠（默认展开） ---------- */
$('histToggle').addEventListener('click', () => sidebarEl.classList.toggle('hist-collapsed'));

/* ---------- 分割条拖拽调宽：左栏 / Agent 面板 ---------- */
function attachResizer(bar, cssVar, onMove){
  bar.addEventListener('pointerdown', e => {
    e.preventDefault();
    bar.setPointerCapture(e.pointerId);
    bar.classList.add('dragging');
    document.body.classList.add('resizing');
    const move = ev => {
      const v = onMove(ev.clientX);
      if (v != null) appEl.style.setProperty(cssVar, v + 'px');
    };
    const up = () => {
      bar.classList.remove('dragging');
      document.body.classList.remove('resizing');
      bar.removeEventListener('pointermove', move);
      bar.removeEventListener('pointerup', up);
      bar.removeEventListener('pointercancel', up);
    };
    bar.addEventListener('pointermove', move);
    bar.addEventListener('pointerup', up);
    bar.addEventListener('pointercancel', up);
  });
}
attachResizer($('resizerSide'), '--side-w', x => Math.max(150, Math.min(window.innerWidth * 0.4, x)));
attachResizer($('resizerAgent'), '--agent-w', x => Math.max(220, Math.min(window.innerWidth * 0.5, window.innerWidth - x)));

/* ---------- Agent 执行状态面板（默认折叠，由右上角折叠钮展开/收起） ---------- */
function setAgentPane(open){
  agentPaneEl.classList.toggle('open', open);
  $('resizerAgent').classList.toggle('hidden', !open);
  $('wcRight').classList.toggle('wcs-open', open);
}
// 右上角折叠钮：面板折叠时点一下展开，展开时点一下收拢
$('wcRight').addEventListener('click', () => setAgentPane(!agentPaneEl.classList.contains('open')));
// 连点折叠钮时阻止冒泡到标题栏的 maximize 逻辑
$('wcRight').addEventListener('dblclick', e => e.stopPropagation());

/* ---------- 临时覆盖层：固定大小、不透明、仅展示层 ---------- */
function openModelOv(){ $('modelOv').classList.add('open'); }
function closeModelOv(){ $('modelOv').classList.remove('open'); }
function openBillOv(){ $('billOv').classList.add('open'); }
function closeBillOv(){ $('billOv').classList.remove('open'); }
function openUsageOv(){ $('usageOv').classList.add('open'); }   // 盖在模型面板之上，模型面板不关闭
function closeUsageOv(){ $('usageOv').classList.remove('open'); }

$('sideModelBtn').addEventListener('click', openModelOv);
$('noModelGo').addEventListener('click', openModelOv);          // 空状态引导卡片里的「模型」
$('modelClose').addEventListener('click', closeModelOv);
$('sideBillBtn').addEventListener('click', () => openBilling());
$('billClose').addEventListener('click', closeBillOv);
$('usageClose').addEventListener('click', closeUsageOv);
// 点击覆盖层外空白区域（面板之外）关闭对应覆盖层
[['modelOv', closeModelOv], ['billOv', closeBillOv], ['usageOv', closeUsageOv]].forEach(([id, fn]) => {
  $(id).addEventListener('mousedown', e => {
    if (e.target.closest('.models, .bill-full')) return;
    fn();
  });
});

/* ---------- 空状态：无可用模型卡 + 空对话输入框居中 ---------- */
function syncChatState(){
  const hasModel = !!modelOptions.length;
  nmBox.hidden = hasModel;                       // 无模型才显示引导卡片
  chatAreaEl.classList.toggle('chat--nomodel', !hasModel);
  syncAgentComposer();                            // 无消息（聊天）或无任务（Agent）→ 输入框垂直居中
}
new MutationObserver(syncChatState).observe(messagesEl, { childList: true });
syncChatState();

/* ===================== 初始化 ===================== */
/* 桌面壳：窗口先显示、后端由壳并行拉起。这里先轮询到后端就绪再加载数据，
   期间给“连接中”提示，避免窗口已开却因后端为空而报错。
   浏览器直连（非桌面）保持原逻辑立即加载，不额外等待。 */
(async function initApp() {
  if (!hasDesktop()) {
    loadConvs();
    loadProviders();
    return;
  }
  $('modelList').innerHTML = `<div class="empty-api" style="padding:12px 8px">正在连接本地服务…</div>`;
  $('convList').innerHTML = `<div class="empty-api" style="padding:12px 8px">正在连接本地服务…</div>`;
  const t0 = Date.now();
  const MAX_WAIT = 30000;
  while (Date.now() - t0 < MAX_WAIT) {
    try { await apiFetch('/mock'); break; } catch (e) { await new Promise((r) => setTimeout(r, 300)); }
  }
  loadConvs();
  loadProviders();
})();
