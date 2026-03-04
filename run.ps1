# send_multi_die_email.ps1
# Opens an Outlook email with HTML-formatted summary of the multi-die tensor dump work

$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)

$mail.Subject = "Multi-Die Tensor Dumps - LLaMA2 stories110M Model Breakdown (2-Die Architecture)"

$htmlBody = @"
<html>
<head>
<style>
  body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #1a1a1a; line-height: 1.5; }
  h1 { color: #0071C5; font-size: 16pt; border-bottom: 2px solid #0071C5; padding-bottom: 6px; }
  h2 { color: #00AEEF; font-size: 13pt; margin-top: 18px; }
  h3 { color: #4a4a4a; font-size: 11pt; margin-top: 14px; }
  .highlight { background-color: #FFF3CD; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
  .die0 { color: #006400; font-weight: bold; }
  .die1 { color: #8B0000; font-weight: bold; }
  .fixed { color: #D35400; font-weight: bold; }
  .key { color: #0071C5; font-weight: bold; }
  table { border-collapse: collapse; margin: 10px 0; font-size: 10pt; }
  th { background-color: #0071C5; color: white; padding: 6px 12px; text-align: left; }
  td { border: 1px solid #ccc; padding: 5px 12px; }
  tr:nth-child(even) { background-color: #f2f7fc; }
  .path-box { background-color: #E8F4FD; border-left: 4px solid #0071C5; padding: 8px 14px; margin: 10px 0; font-family: Consolas, monospace; font-size: 10pt; }
  .section { margin-left: 12px; }
  ul { margin-top: 4px; }
  li { margin-bottom: 3px; }
  .tag-boss { background-color: #d4edda; color: #155724; padding: 1px 6px; border-radius: 3px; font-size: 9pt; }
  .tag-secondary { background-color: #f8d7da; color: #721c24; padding: 1px 6px; border-radius: 3px; font-size: 9pt; }
</style>
</head>
<body>

<h1>&#x1F9E9; Multi-Die Model Breakdown &mdash; Tensor Dump Files Ready</h1>

<p>Hi Team,</p>

<p>I've completed the <span class="key">multi-die architecture breakdown</span> for the <b>LLaMA2 stories110M</b> model and generated full per-die tensor dump files. These dumps show exactly how every weight matrix, activation, and KV cache entry is distributed across <span class="die0">Die 0 (Boss)</span> and <span class="die1">Die 1 (Secondary)</span>.</p>

<p>The dump files have been placed here:</p>
<div class="path-box">
OneDrive - Intel Corporation\Model On Silicon - Live Oaks - Live Oaks Documents\StoryOut\Multi_die\die_dumps
</div>

<h2>&#x1F527; What Was Done</h2>

<h3>1. Architecture Corrections (Critical Fixes)</h3>
<div class="section">
<p>Two significant issues were identified and corrected in the multi-die split approach:</p>
<ul>
  <li><span class="fixed">KV Cache Split Fix:</span> The previous implementation split the KV cache <b>by positions</b> (512 positions per die) &mdash; this is <u>incorrect</u> because each attention head needs access to <b>ALL</b> positions to compute attention scores. The fix: split by <b>heads</b> instead. Each die now stores <b>all 1024 positions</b> but only <b>6 of the 12 heads</b> (384-wide per die).</li>
  <li><span class="fixed">Wq/Wk/Wv Separate Split Fix:</span> Previously, Wq, Wk, Wv were merged into a single 2304&times;768 WQKV block and then row-split &mdash; this meant rows from different weight types (Q vs K vs V) got mixed across dies unpredictably. The fix: split each of <b>Wq, Wk, Wv independently</b> as three separate 768&times;768 matrices.</li>
</ul>
</div>

<h3>2. Model Specifications</h3>
<div class="section">
<table>
  <tr><th>Parameter</th><th>Value</th></tr>
  <tr><td>Model</td><td>stories110M (LLaMA2)</td></tr>
  <tr><td>Dimension</td><td>768</td></tr>
  <tr><td>Hidden Dim (FFN)</td><td>2048</td></tr>
  <tr><td>Layers</td><td>12</td></tr>
  <tr><td>Attention Heads</td><td>12 (6 per die)</td></tr>
  <tr><td>Head Size</td><td>64</td></tr>
  <tr><td>Vocab Size</td><td>32,000</td></tr>
  <tr><td>Sequence Length</td><td>1024</td></tr>
  <tr><td>Precision</td><td>BF16</td></tr>
  <tr><td>Dies</td><td>2 (1536 RAMULADs each)</td></tr>
</table>
</div>

<h3>3. Weight Distribution Across Dies</h3>
<div class="section">
<table>
  <tr><th>Component</th><th>Full Size</th><th>Die 0 Rows</th><th>Die 1 Rows</th><th>Split Method</th></tr>
  <tr><td><b>Wq</b> (per layer)</td><td>768 &times; 768</td><td>384 rows</td><td>384 rows</td><td>Row-split (128-group alternating)</td></tr>
  <tr><td><b>Wk</b> (per layer)</td><td>768 &times; 768</td><td>384 rows</td><td>384 rows</td><td>Row-split (128-group alternating)</td></tr>
  <tr><td><b>Wv</b> (per layer)</td><td>768 &times; 768</td><td>384 rows</td><td>384 rows</td><td>Row-split (128-group alternating)</td></tr>
  <tr><td><b>Wo</b> (per layer)</td><td>768 &times; 768</td><td>384 rows</td><td>384 rows</td><td>Row-split</td></tr>
  <tr><td><b>W1</b> (per layer)</td><td>2048 &times; 768</td><td>1024 rows</td><td>1024 rows</td><td>Row-split</td></tr>
  <tr><td><b>W3</b> (per layer)</td><td>2048 &times; 768</td><td>1024 rows</td><td>1024 rows</td><td>Row-split</td></tr>
  <tr><td><b>W2</b> (per layer)</td><td>768 &times; 2048</td><td>384 rows</td><td>384 rows</td><td>Row-split (2048-wide)</td></tr>
  <tr><td><b>Wcls</b></td><td>32000 &times; 768</td><td>16000 rows</td><td>16000 rows</td><td>Row-split</td></tr>
  <tr><td><b>KV Cache</b> (per layer)</td><td>1024 pos &times; 768</td><td>1024 pos &times; 384 (heads 0-5)</td><td>1024 pos &times; 384 (heads 6-11)</td><td><span class="highlight">Head-split</span></td></tr>
</table>
</div>

<h3>4. Die Roles</h3>
<div class="section">
<table>
  <tr><th>Responsibility</th><th><span class="die0">Die 0 (Boss)</span> <span class="tag-boss">PRIMARY</span></th><th><span class="die1">Die 1</span> <span class="tag-secondary">SECONDARY</span></th></tr>
  <tr><td>Token Embeddings</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>RoPE (Rotary Pos Encoding)</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>RMS Norm (attn, ffn, final)</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>Weight Rows (Wq,Wk,Wv,Wo,W1,W3,W2)</td><td>&#x2705; (half)</td><td>&#x2705; (half)</td></tr>
  <tr><td>Wcls (Classifier)</td><td>&#x2705; (half)</td><td>&#x2705; (half)</td></tr>
  <tr><td>Attention Heads 0-5</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>Attention Heads 6-11</td><td>&mdash;</td><td>&#x2705;</td></tr>
  <tr><td>KV Cache (heads 0-5, all positions)</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>KV Cache (heads 6-11, all positions)</td><td>&mdash;</td><td>&#x2705;</td></tr>
  <tr><td>Residual Accumulation</td><td>&#x2705;</td><td>&mdash;</td></tr>
  <tr><td>Logits / Sampling</td><td>&#x2705;</td><td>&mdash;</td></tr>
</table>
</div>

<h3>5. Generated Dump Files</h3>
<div class="section">
<p>All files are in the shared directory above. For <b>1 token position across all 12 layers</b>:</p>
<table>
  <tr><th>File</th><th>Content</th><th>Size</th></tr>
  <tr><td><code>tensor_dump_bf16_hw_die0_outer.txt</code></td><td>Die 0: embeddings, RoPE, final RMS, Wcls weights, logits</td><td>~126 MB</td></tr>
  <tr><td><code>tensor_dump_bf16_hw_die1_outer.txt</code></td><td>Die 1: Wcls weights, token index</td><td>~125 MB</td></tr>
  <tr><td><code>tensor_dump_bf16_hw_die0_layer{0-11}.txt</code></td><td>Die 0: RMS, heads 0-5, weight rows, KV cache, partials</td><td>~36 MB each</td></tr>
  <tr><td><code>tensor_dump_bf16_hw_die1_layer{0-11}.txt</code></td><td>Die 1: heads 6-11, weight rows, KV cache, partials</td><td>~36 MB each</td></tr>
  <tr><td><code>output_tokens_hw_multi_die.txt</code></td><td>Generated token log</td><td>&lt;1 KB</td></tr>
</table>
<p><b>Total:</b> 28 files, ~1.1 GB. All values in BF16 hex format, 8 values per line with row/col annotations.</p>
</div>

<h3>6. Dump Format</h3>
<div class="section">
<p>Each section in the dump files follows this structure:</p>
<div class="path-box">
pos0_layer0_wq<br/>
rows: 384<br/>
col:&nbsp; 768<br/>
*<br/><br/>
3E04 3DED 3DE5 3E07 3DFA 3E0F 3DE9 3E17 &nbsp;// row: 0 | col start:0 &nbsp;&nbsp;| col end: 7<br/>
...
</div>
<p>This makes it straightforward to cross-reference with the hardware command sequence and verify values against RTL simulation.</p>
</div>

<h2>&#x1F4C1; Files Modified / Created</h2>
<div class="section">
<ul>
  <li><b>multi_die_config.py</b> &mdash; Added head-based split constants (HEADS_PER_DIE=6, KV_DIM_PER_DIE=384, separate Wq/Wk/Wv line counts)</li>
  <li><b>multi_die_generate_weights.py</b> &mdash; Updated to split Wq/Wk/Wv independently &amp; head-split KV cache</li>
  <li><b>print_weight_dims.py</b> &mdash; Updated tables to reflect new layout</li>
  <li><b>llama2_bf16_hw_multi_die.py</b> &mdash; <span class="highlight">NEW</span> &mdash; Full inference script producing per-die tensor dumps</li>
</ul>
</div>

<p>Let me know if you have any questions or need the dumps regenerated with different parameters (e.g., multiple token positions, specific layers, or different prompts).</p>

<p>Thanks,</p>

</body>
</html>
"@

$mail.HTMLBody = $htmlBody
$mail.Display()

Write-Host "Email draft opened in Outlook." -ForegroundColor Green
