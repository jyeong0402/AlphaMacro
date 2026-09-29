const API = window.ALPHAMACRO_API || "http://localhost:8000";
let token = localStorage.getItem("alphamacro_token");
let chart;
const $ = (id) => document.getElementById(id);
const fmt = (value, digits = 2) => value == null ? "—" : Number(value).toFixed(digits);
async function api(path, options = {}) {
  const headers = {"Content-Type":"application/json", ...(options.headers || {})};
  if (token) headers.Authorization = "Bearer " + token;
  const response = await fetch(`${API}${path}`, {...options, headers});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Request failed");
  return body;
}
async function loadOverview() {
  const ticker = $("ticker").value.trim().toUpperCase(), indicator = $("indicator").value.trim();
  $("news-ticker").textContent = ticker; $("overview-error").classList.add("hidden");
  try {
    const [overview, sentiment, news] = await Promise.all([
      api(`/api/v1/macro/correlation?ticker=${encodeURIComponent(ticker)}&indicator=${encodeURIComponent(indicator)}&period=${$("period").value}`),
      api(`/api/v1/ai/sentiment/${encodeURIComponent(ticker)}`), api(`/api/v1/ai/news/${encodeURIComponent(ticker)}`)
    ]);
    $("correlation").textContent = fmt(overview.correlation, 3); $("rsi").textContent = fmt(overview.latest_rsi);
    $("macd").textContent = fmt(overview.latest_macd); $("chart-caption").textContent = `${ticker} / ${indicator}`;
    $("sentiment").textContent = fmt(sentiment.sentiment_score, 3); $("sentiment-label").textContent = sentiment.sentiment_label || "No data";
    $("news-list").innerHTML = news.length ? news.map(item => `<div class="news-item"><a href="${item.url || "#"}" target="_blank" rel="noreferrer">${escapeHtml(item.title)}</a><div class="news-meta">${escapeHtml(item.source || "Market feed")} · ${item.published_at ? new Date(item.published_at).toLocaleDateString() : "Recent"}</div></div>`).join("") : '<div class="empty">No headlines for this symbol.</div>';
    if (chart) chart.destroy();
    chart = new Chart($("correlation-chart"), {type:"line", data:{labels:overview.dates, datasets:[{label:"Stock return",data:overview.stock_returns,borderColor:"#3f6df6",pointRadius:0,borderWidth:2},{label:"Macro return",data:overview.indicator_returns,borderColor:"#e85d43",pointRadius:0,borderWidth:2}]}, options:{responsive:true, interaction:{mode:"index",intersect:false}, plugins:{legend:{labels:{usePointStyle:true,boxWidth:8}}}, scales:{x:{display:false},y:{grid:{color:"#eef1f5"},ticks:{callback:v=>`${(v*100).toFixed(1)}%`}}}}});
  } catch (error) { $("overview-error").textContent = error.message; $("overview-error").classList.remove("hidden"); }
}
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char])); }
$("refresh").addEventListener("click", loadOverview); loadOverview();
async function runBacktest(event) {
  event.preventDefault(); const form = new FormData(event.target); const conditions = form.get("buy_indicator") && form.get("buy_value") ? [{indicator:form.get("buy_indicator"),operator:form.get("buy_operator"),value:Number(form.get("buy_value"))}] : [];
  const result = $("backtest-result"); result.classList.remove("hidden"); result.textContent = "Running…";
  try {
    const data = await api("/api/v1/backtest/run",{method:"POST",body:JSON.stringify({ticker:form.get("ticker"),start_date:form.get("start_date"),end_date:form.get("end_date"),initial_capital:Number(form.get("initial_capital")),buy_conditions:conditions,sell_conditions:[]})});
    const benchmark = data.benchmark_return == null ? "" : ` · ${data.benchmark_ticker} ${fmt(data.benchmark_return * 100)}% · excess ${fmt(data.excess_return * 100)}%`;
    result.textContent = `${data.ticker}: ${fmt(data.total_return * 100)}% return · final value ${fmt(data.final_value)} · ${data.trade_count} trades${benchmark}`;
  }
  catch (error) { result.textContent = error.message + (error.message.includes("authenticated") ? " Please sign in." : ""); }
}
$("backtest-form").addEventListener("submit", runBacktest);
$("login-open").addEventListener("click", () => $("login-dialog").showModal());
$("login-form").addEventListener("submit", async event => { event.preventDefault(); const form = new FormData(event.target); try { const data = await api("/api/v1/auth/login",{method:"POST",body:JSON.stringify({email:form.get("email"),password:form.get("password")})}); token=data.access_token; localStorage.setItem("alphamacro_token",token); $("login-dialog").close(); $("login-open").textContent="Signed in"; } catch(error) { $("login-message").textContent=error.message; }});
api("/health").then(() => { $("api-status").textContent="API connected"; $("api-status").parentElement.classList.add("ok"); }).catch(() => $("api-status").textContent="API offline");
