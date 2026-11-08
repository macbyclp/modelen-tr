# -*- coding: utf-8 -*-
"""English content. Keys match content_tr.py. %%KEY%% placeholders are filled by build.py.
The Turkish text prevails if the two differ."""

FILES = {"index": "index", "nasil-calisir": "how-it-works", "yol-haritasi": "roadmap", "sss": "faq",
         "katil": "join", "hakkinda": "about", "iletisim": "contact", "gizlilik": "privacy",
         "kvkk": "kvkk-notice", "kullanim-sartlari": "terms", "cerez": "cookies",
         "gonullu-sartlari": "volunteer-terms", "koordinator-ol": "become-coordinator", "koordinatorler": "koordinatorler", "akis": "akis", "topluluk-kurallari": "community-rules", "katki-sartlari": "contributing", "lisans": "license"}

PAGES = {}

PAGES["index"] = dict(
    title="Modelen · Open AI for Turkish, trained together by the community",
    desc="Modelen aims to train open Turkish language models on volunteers' GPUs. We are at the research stage.",
    body="""
<section class="hero prose">
  <p><span class="status">Research stage · no released model yet</span></p>
  <h1>Open AI for Turkish, trained together by the community.</h1>
  <p class="lead">Modelen builds openly licensed language models that Turkish-speaking developers and organisations can run locally. Our goal is to train them not in a single organisation's data centre but on volunteers' idle GPUs.</p>
  <div class="actions">
    <a class="btn" href="join.html">I want to volunteer</a>
    <a class="btn ghost" href="how-it-works.html">How it works</a>
  </div>
</section>

<div class="grid">
  <div class="card"><h3>Open</h3><p>Code and model weights are planned under Apache-2.0. Training-data sources and their licences will be listed openly.</p></div>
  <div class="card"><h3>Turkish first</h3><p>Turkish morphology affects both quality and cost in general-purpose models. We measure Turkish and build for it.</p></div>
  <div class="card"><h3>Community owned</h3><p>Contributions are kept in a transparent record. No money or crypto rewards to begin with; a contribution record and a say in direction instead.</p></div>
  <div class="card"><h3>Privacy respecting</h3><p>The volunteer client runs only the training job and does not access your files or personal data. That is the design principle, and the client will be open source.</p></div>
</div>

<div class="prose">
<h2>Where are we now?</h2>
<p>To be honest: Modelen is an early research project. We have no public model and no volunteer client yet. So far we have:</p>
<ul>
  <li>Run a small-scale simulation of sparse-synchronisation (DiLoCo-style) training used in volunteer networks.</li>
  <li>Tried adapting an open base model (Qwen3-0.6B-Base, Apache-2.0) with Turkish text on a consumer 8&nbsp;GB GPU.</li>
  <li>Results are promising but limited: single runs, small data, no real network. See the <a href="roadmap.html">roadmap</a>.</li>
</ul>
<p>We make no promises about what comes later on this page; we show what we have published.</p>

<h2>Who is it for?</h2>
<p>Developers, researchers and organisations working in Turkish. The target product form is locally runnable models and an API.</p>
</div>
""")

PAGES["nasil-calisir"] = dict(
    title="How it works · Modelen",
    desc="How distributed training on volunteer GPUs is planned to work at Modelen: sparse synchronisation, LoRA adapters and verification.",
    body="""
<div class="prose">
<h1>How it works</h1>
<p class="lead">In short: instead of training a large model from scratch, we adapt an open base model to Turkish and split that adaptation across many volunteer computers.</p>

<h2>1. We start from an open base</h2>
<p>Training from scratch takes months on a single GPU. Instead we take a suitably licensed open base model (Qwen3-0.6B-Base, Apache-2.0, in our first experiments) and apply continued pre-training on Turkish text.</p>

<h2>2. We train only a small part</h2>
<p>With LoRA we freeze the base model and train only a small adapter. In our experiments the adapter is about 40&nbsp;MB while the base model is about 1.2&nbsp;GB. That reduces a volunteer GPU's memory needs and the data sent over the network.</p>

<h2>3. Sparse synchronisation</h2>
<p>Each volunteer computer works on its own data slice for a while; then only the adapter updates are collected and merged. This approach is called DiLoCo. In one simulation we moved about 25 times less data than training that synchronises every step, with a very close result. That simulation was single-seed, small-scale, with no real network; it does not guarantee the same result in the real world.</p>

<h2>4. Trust and verification</h2>
<p>A volunteer machine may send faulty or malicious updates. Our plan: verify the same work on several machines, check update size and consistency, and add small known test tasks. These mechanisms are still under development.</p>

<h2>5. What happens on your computer?</h2>
<ul>
  <li>The client will be open source; you can read what it runs.</li>
  <li>Updates will be signed.</li>
  <li>The client runs only the training job and does not access your files or personal data. This must be verifiable once the client is released.</li>
  <li>You can stop at any time.</li>
</ul>

<h2>What don't we know yet?</h2>
<p>We have not measured how results change at 1&nbsp;billion parameters and above, over real internet conditions, with different data slices, and with volunteer dropout and malicious contributions. These are next on our roadmap.</p>
</div>
""")

PAGES["yol-haritasi"] = dict(
    title="Roadmap · Modelen",
    desc="Modelen roadmap: research, Turkish adaptation, volunteer client, closed pilot and open network. No date commitments.",
    body="""
<div class="prose">
<h1>Roadmap</h1>
<p class="lead">We list the stages in order, without date commitments. When a stage ends we will publish what we measured, together with what we could not find.</p>

<ol class="timeline">
  <li class="done"><b>0. Research and simulation · done (first round)</b>Sparse synchronisation on a small model, outer-optimiser sweeps and an adapter-scale DiLoCo simulation. Limits: small scale, single seed, no real network.</li>
  <li class="done"><b>1. Turkish adaptation · first experiment done</b>Short continued pre-training with LoRA on Qwen3-0.6B-Base on a consumer 8&nbsp;GB GPU. Turkish language modelling improved; we saw no meaningful improvement on a Turkish benchmark (TurkishMMLU) and measured a slight loss in English.</li>
  <li><b>2. More and more varied data</b>More Turkish data, English replay mix, tokenizer evaluation, a 1.7B-scale base.</li>
  <li><b>3. Volunteer client (alpha)</b>Open-source client with signed updates; contribution verification; first internal tests.</li>
  <li><b>4. Closed pilot</b>Training over a real network with a small group of volunteers; fault and security trials.</li>
  <li><b>5. Open network and first release</b>Release of weights, code and the list of data sources under Apache-2.0 / applicable licences.</li>
</ol>

<h2>Known risks</h2>
<ul>
  <li>Research suggests weights trained with sparse synchronisation may not combine well with later standard training; we will test this ourselves.</li>
  <li>Training-data licences (e.g. CC BY-SA data) need legal review for the weights we release.</li>
  <li>Open Turkish models already exist; our difference has to be measurable improvement and community ownership.</li>
</ul>
</div>
""")

PAGES["sss"] = dict(
    title="FAQ · Modelen",
    desc="Frequently asked questions about Modelen: volunteering, payment, security, licence and data.",
    body="""
<div class="prose">
<h1>Frequently asked questions</h1>
<details><summary>Do you have a released model?</summary><p>No. We are at the research stage. When we release a first model we will state clearly what it is, how it was measured and its limits.</p></details>
<details><summary>What do I need to volunteer?</summary><p>The initial target is an NVIDIA graphics card with at least 8&nbsp;GB of memory. This may change. The volunteer client is not released yet; if you are interested, write to us from the <a href="join.html">Join page</a>.</p></details>
<details><summary>Will I earn money or crypto?</summary><p>Not to begin with. Your contribution is kept in a transparent record and you get a say in the model's direction. We do not plan to distribute money or tokens.</p></details>
<details><summary>Can it harm my computer?</summary><p>Heavy GPU use increases power draw, heat and fan noise and may affect hardware lifespan. The client will offer settings to limit this. The decision is yours and you can stop at any time.</p></details>
<details><summary>Does it access my personal data?</summary><p>Our design principle: the client runs only the training job and does not access your files or personal data. Only technical information (e.g. GPU model, memory, version) is shared. Details are in the <a href="kvkk-notice.html">Data Notice</a>, which will be updated when the client is released.</p></details>
<details><summary>What data do you train on?</summary><p>In early experiments we used a subset of Turkish Wikipedia. For later work we will publish all data sources and their licences.</p></details>
<details><summary>What is the licence?</summary><p>We aim for Apache-2.0 for code and model weights. Licence requirements arising from training data will be settled after legal review. See <a href="license.html">Licence</a>.</p></details>
<details><summary>Why don't you train from scratch?</summary><p>Training a 1-billion-parameter model from scratch on one consumer GPU takes months and does not fit in memory. Adapting an open base is much cheaper and faster. Training from scratch may become an option later.</p></details>
<details><summary>Who are you?</summary><p>Modelen Alternatif Eğitim Topluluğu. See <a href="about.html">About</a>.</p></details>
</div>
""")

PAGES["katil"] = dict(
    title="Join · Modelen",
    desc="How to join Modelen as a volunteer: the volunteer client is not released yet; interested people can write by email.",
    body="""
<div class="prose">
<h1>Join</h1>
<p class="lead">The volunteer client is not released yet. We will announce it here when it is ready.</p>
<h2>What can you do now?</h2>
<ul>
  <li><b>Stay informed:</b> write to <a href="mailto:%%EPOSTA%%?subject=Volunteer%20interest">%%EPOSTA%%</a> with the subject "Volunteer". Your email address is used only for Modelen announcements; see the <a href="kvkk-notice.html">Data Notice</a>.</li>
  <li><b>Contribute:</b> we also need help with code, data evaluation, Turkish benchmarks and legal/security review. See the <a href="contributing.html">contribution terms</a>.</li>
</ul>
<h2>What we expect from volunteers</h2>
<ul>
  <li>Target hardware: an NVIDIA graphics card with at least 8&nbsp;GB of memory (may change).</li>
  <li>For under-18s, parental or guardian consent.</li>
  <li>Please read the <a href="volunteer-terms.html">volunteer participation terms</a>.</li>
</ul>
<p><b>There is no money or crypto reward.</b> There is a contribution record and a say in direction.</p>
</div>
""")

PAGES["hakkinda"] = dict(
    title="About · Modelen",
    desc="About Modelen Alternatif Eğitim Topluluğu: mission, principles and community information.",
    body="""
<div class="prose">
<h1>About</h1>
<p class="lead">Modelen is a venture aiming to build open, community-owned AI models for Turkish.</p>
<h2>Mission</h2>
<p>To offer openly and transparently trained models that Turkish-speaking developers and organisations can use without having to send their data abroad.</p>
<h2>Principles</h2>
<ul>
  <li><b>Transparency:</b> we publish what we measured and what we could not measure.</li>
  <li><b>Openness:</b> code and weights are released under open licences.</li>
  <li><b>Community ownership:</b> contributions are on record and decisions are made in the open.</li>
  <li><b>Privacy:</b> we do not access personal data on volunteers' devices.</li>
  <li><b>No overclaiming:</b> we say only as much as we have proven.</li>
</ul>
<h2>Community information</h2>
<table>
  <tr><th>Name</th><td>Modelen Alternatif Eğitim Topluluğu</td></tr>
  <tr><th>Domain</th><td>modelen.tr</td></tr>
  <tr><th>Contact</th><td>%%EPOSTA%%</td></tr>
</table>
</div>
""")

PAGES["iletisim"] = dict(
    title="Contact · Modelen",
    desc="Contact Modelen: general questions, volunteering, press and personal-data requests via one email address.",
    body="""
<div class="prose">
<h1>Contact</h1>
<p class="lead">One address for everything: <a href="mailto:%%EPOSTA%%">%%EPOSTA%%</a></p>
<ul>
  <li><b>General, volunteering, press:</b> put your topic in the subject line.</li>
  <li><b>Personal-data requests (KVKK):</b> use "KVKK Request" as the subject. See the <a href="kvkk-notice.html">Data Notice</a>.</li>
  <li><b>Security reports:</b> use "Security" as the subject. We thank you for responsible disclosure; details are in <code>/.well-known/security.txt</code>.</li>
</ul>
</div>
""")

PAGES["gizlilik"] = dict(
    legal=True,
    title="Privacy policy · Modelen",
    desc="Privacy policy for the Modelen website: what data is processed, cookie use and your rights.",
    body="""
<div class="prose">
<h1>Privacy policy</h1>
<p><small>Last updated: %%TARIH_EN%%</small></p>
<p>This policy applies to the modelen.tr website. It will be updated, together with the Data Notice, when the volunteer client is released.</p>
<h2>In short</h2>
<ul>
  <li>We use no advertising, tracking or analytics tools on the site. Only if you create an account or sign in, strictly necessary cookies are used for your session.</li>
  <li>We load no third-party scripts, fonts or embedded content.</li>
  <li>If you email us, we process your email address and message only to reply.</li>
</ul>
<h2>Data we process</h2>
<ul>
  <li><b>Server logs:</b> the hosting provider (%%BARINDIRMA%%) may record IP address, request time and browser information for security and operation. Retention periods are subject to the provider's policy and applicable law.</li>
  <li><b>Email correspondence:</b> name (if given), email address and message content.</li>
  <li><b>Profile and community content:</b> profile details (display name, username, bio, photo, social links), posts, follow and block records, reports. A profile is <b>private by default</b>; only if you make it "public" are the profile details above and your posts published on public pages (your email is never shown). EXIF location and device data are removed from photos on upload. You can hide your profile at any time or delete it with your account.</li>
  <li><b>Account and coordinator application:</b> if you register, your name, email address and password (the password is stored only as an irreversible hash); if you apply as a coordinator, the project name, descriptions, links, the coordinator address if any, and a contact email. Once approved, the project name, descriptions, link and address are published on a public page; your contact email and account details are visible to admins only. You can delete your account from the panel at any time; the account, application and page are permanently removed.</li>
</ul>
<h2>Your rights</h2>
<p>For your rights under Turkish Law No. 6698 on the Protection of Personal Data (KVKK) and how to apply, see the <a href="kvkk-notice.html">Data Notice</a>.</p>
<h2>Changes</h2>
<p>When this policy is updated, the date at the top changes.</p>
</div>
""")

PAGES["kvkk"] = dict(
    legal=True,
    title="KVKK data notice · Modelen",
    desc="Modelen's notice under Turkish Law No. 6698 (KVKK): data controller, purposes, legal bases and your rights.",
    body="""
<div class="prose">
<h1>Notice on the Processing of Personal Data</h1>
<p><small>Law No. 6698, Art. 10 · Last updated: %%TARIH_EN%% · Convenience translation; the Turkish text prevails.</small></p>
<h2>1. Data controller</h2>
<p>Modelen Alternatif Eğitim Topluluğu · Email: %%EPOSTA%%</p>
<h2>2. Data processed, purposes and legal bases</h2>
<table>
  <tr><th>Data</th><th>Purpose</th><th>Legal basis</th></tr>
  <tr><td>Transaction security data (IP address, request time, browser information; via the hosting provider)</td><td>Secure and continuous operation of the site; record-keeping required by law</td><td>Legal obligation; legitimate interest (Art. 5/2-f)</td></tr>
  <tr><td>Contact data (name, email, message content)</td><td>Replying to your requests; volunteer and announcement communication</td><td>Legitimate interest; where necessary for entering into a contract, Art. 5/2-c</td></tr>
  <tr><td>Profile and community content (display name, username, bio, photo, social links, posts, follow/block/report records)</td><td>Providing community features, preventing abuse and moderation</td><td>Explicit consent (details made public); legitimate interest (security and moderation)</td></tr>
  <tr><td>Account and application data (name, email, password hash, project details, contact email, session record)</td><td>Running the account, evaluating the coordinator application and publishing approved coordinators</td><td>Entering into and performing a contract (Art. 5/2-c); explicit consent (published project details)</td></tr>
</table>
<p>When the volunteer client is released, the technical data it processes (e.g. GPU model, memory, operating system, client version, uptime, contribution records) will be added to this notice. Our principle is that the client collects no identity data, file contents or personal content.</p>
<h2>3. Transfers</h2>
<p>Your data may be transferred to the hosting and email service providers we use (%%BARINDIRMA%%) and to competent authorities where legally required. Any transfer abroad follows the conditions in Article 9 of the Law.</p>
<h2>4. Method of collection</h2>
<p>Data is collected automatically during your visit to the website and through emails you send us.</p>
<h2>5. Your rights (Art. 11)</h2>
<ul>
  <li>To learn whether your personal data is processed,</li>
  <li>To request information if it has been processed,</li>
  <li>To learn the purpose of processing and whether it is used accordingly,</li>
  <li>To know the third parties to whom data is transferred in Türkiye or abroad,</li>
  <li>To request correction if processed incompletely or inaccurately,</li>
  <li>To request erasure or destruction under the conditions in the Law and to have this notified to third parties to whom data was transferred,</li>
  <li>To object to an outcome against you arising from analysis exclusively by automated systems,</li>
  <li>To request compensation for damage caused by unlawful processing.</li>
</ul>
<h2>6. How to apply</h2>
<p>You may submit your request, with information identifying you, by email to %%EPOSTA%% (subject: "KVKK Request"), using the methods set out in the Communiqué on Procedures and Principles of Applications to the Data Controller. Requests are concluded as soon as possible and at the latest within thirty days. If your request is rejected, the response is insufficient, or no response is given in time, you may complain to the Personal Data Protection Board within thirty days of learning the response and in any case within sixty days of the request.</p>
</div>
""")

PAGES["kullanim-sartlari"] = dict(
    legal=True,
    title="Website terms of use · Modelen",
    desc="Terms of use for the Modelen website: content, intellectual property, liability and governing law.",
    body="""
<div class="prose">
<h1>Website terms of use</h1>
<p><small>Last updated: %%TARIH_EN%% · Convenience translation; the Turkish text prevails.</small></p>
<h2>1. Scope</h2>
<p>These terms govern use of the modelen.tr website. By using the site you accept them. Separate terms apply to volunteering computing power and to code/data contributions: <a href="volunteer-terms.html">Volunteer Terms</a>, <a href="contributing.html">Contribution Terms</a>.</p>
<h2>2. Informational purpose</h2>
<p>Site content is for general information. Modelen is at the research stage; results, plans and measurements on the site may change and are not a guarantee or commitment.</p>
<h2>3. Intellectual property</h2>
<p>Unless stated otherwise, site text, images and the name and logo "Modelen" belong to %%UNVAN%%. Modelen software and models, once released, may be used under the applicable licences (Apache-2.0); that licence does not grant rights to the name and logo.</p>
<h2>4. Limitation of liability</h2>
<p>The site is provided "as is". To the extent permitted by applicable law, we are not liable for indirect damages arising from use of the site. This clause does not affect liabilities that the law does not allow to be limited.</p>
<h2>5. External links</h2>
<p>We are not responsible for the content of third-party sites we link to.</p>
<h2>6. Governing law and jurisdiction</h2>
<p>Turkish law applies. For disputes, %%MAHKEME%% have jurisdiction; your rights under consumer legislation are reserved.</p>
<h2>7. Changes</h2>
<p>We may update these terms; the current version is published on this page.</p>
</div>
""")

PAGES["cerez"] = dict(
    legal=True,
    title="Cookie policy · Modelen",
    desc="The Modelen website does not use cookies. This page explains our cookie policy.",
    body="""
<div class="prose">
<h1>Cookie policy</h1>
<p><small>Last updated: %%TARIH_EN%%</small></p>
<p>modelen.tr places no advertising, tracking or analytics cookies or similar technologies and does not write data to your browser's local storage.</p>
<p>If you only read the site, no cookies are used. If you create an account or sign in, two <b>strictly necessary</b> cookies are set for the service to work: a session cookie (<code>ms</code>, keeps you signed in, at most 14 days) and a form-security cookie (<code>mc</code>, prevents forged requests). Both are sent only to this site, cannot be read by scripts (HttpOnly), and the session cookie is invalidated when you sign out or delete your account. No separate consent is requested for strictly necessary cookies.</p>
<p>The hosting provider may keep technical information such as IP addresses in server logs; see the <a href="privacy.html">Privacy policy</a>.</p>
<p>If we add other cookies or an analytics tool in future, we will update this policy before using them and ask for your explicit consent where required.</p>
</div>
""")

PAGES["gonullu-sartlari"] = dict(
    legal=True,
    title="Volunteer participation terms · Modelen",
    desc="Draft Modelen volunteer terms: conditions for volunteering GPU power, security principles and responsibilities.",
    body="""
<div class="prose">
<h1>Volunteer participation terms</h1>
<p><small>Last updated: %%TARIH_EN%% · Not binding until the client is released · Convenience translation; the Turkish text prevails.</small></p>
<p>These terms are for people who will provide computing power to Modelen's volunteer training network ("Volunteer"). The volunteer client has not been released; this text shows the planned conditions.</p>
<h2>1. Voluntary and unpaid</h2>
<p>Participation is optional and unpaid. No money, crypto asset or other payment is made. Your contributions appear in a transparent contribution record (under a pseudonym if you wish).</p>
<h2>2. Age</h2>
<p>People under 18 may participate only with parental or guardian consent.</p>
<h2>3. Client and security principles</h2>
<ul>
  <li>The client is released as open source; updates are signed.</li>
  <li>The client runs only the training job and does not access your files, browser data, screen or credentials.</li>
  <li>Technical information shared: GPU model and memory, operating system, client version, uptime and contribution results.</li>
  <li>You may stop and remove it at any time; no data is collected from the client after removal.</li>
</ul>
<h2>4. Volunteer's obligations</h2>
<ul>
  <li>Do not modify the client to send fake, faulty or harmful contributions.</li>
  <li>Do not run it without permission on a computer you do not own or are not authorised to use.</li>
  <li>Keep your contribution-record details accurate.</li>
</ul>
<h2>5. Hardware and energy</h2>
<p>Heavy GPU use increases power consumption, heat and noise and may affect hardware lifespan. You decide the usage time and power limit. Modelen's liability is limited to the extent permitted by law; this limitation does not affect mandatory provisions.</p>
<h2>6. Ending participation</h2>
<p>You may leave at any time. We reserve the right to remove contributions that threaten security or violate these terms.</p>
<h2>7. Personal data</h2>
<p>Processing of personal data is covered by the <a href="kvkk-notice.html">Data Notice</a>.</p>
<h2>8. Governing law</h2>
<p>Turkish law; competent courts: %%MAHKEME%%.</p>
</div>
""")

PAGES["katki-sartlari"] = dict(
    legal=True,
    title="Contribution terms · Modelen",
    desc="Terms for contributing code, data and documentation to Modelen: Apache-2.0 and the Developer Certificate of Origin.",
    body="""
<div class="prose">
<h1>Contribution terms</h1>
<p><small>Last updated: %%TARIH_EN%% · Convenience translation; the Turkish text prevails.</small></p>
<p>Contributions of code, documentation, benchmarks or data are valuable to us. To allow them to be used properly, these terms apply.</p>
<h2>1. Licence</h2>
<p>Your contribution is licensed under the licence of the project you contribute to (Apache-2.0 for code and models). This is consistent with Section 5, "Submission of Contributions", of Apache-2.0. Your authorship credit is preserved.</p>
<h2>2. Developer Certificate of Origin (DCO)</h2>
<p>By adding a <code>Signed-off-by: Your Name &lt;email&gt;</code> line to each commit message you accept version 1.1 of the Developer Certificate of Origin (text: developercertificate.org). In short: you have the right to make the contribution and agree to it being shared under the project licence.</p>
<h2>3. Data contributions</h2>
<p>For data contributions you must state the source, the licence and whether it contains personal data. Data that contains personal data, lacks copyright permission or has an unclear licence is not accepted.</p>
<h2>4. Review</h2>
<p>We review contributions for quality, security and licence compatibility and reserve the right to decline them.</p>
<h2>5. Conduct</h2>
<p>We expect respectful and constructive communication. See the <a href="community-rules.html">Community rules</a> for conduct and the <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub repository</a> for the code.</p>
</div>
""")

PAGES["lisans"] = dict(
    title="Licence · Modelen",
    desc="Modelen code and model licence: Apache License 2.0. Notes on training-data licences and trademark use.",
    body="""
<div class="prose">
<h1>Licence</h1>
<p>Modelen code and model weights will be offered under the <b>Apache License 2.0</b> once released. Full text: <a href="https://www.apache.org/licenses/LICENSE-2.0">apache.org/licenses/LICENSE-2.0</a> and the <code>LICENSE</code> file in the repository.</p>
<h2>Important notes</h2>
<ul>
  <li><b>Base model:</b> Qwen3-0.6B-Base (Alibaba Cloud), used in our first experiments, is licensed under Apache-2.0. We will state the licence of every base model we use.</li>
  <li><b>Training data:</b> Turkish Wikipedia text used in early experiments is published under licences such as CC BY-SA / GFDL. The conditions under which weights trained on such data can be released are subject to legal review; we will announce the outcome here.</li>
  <li><b>Trademark:</b> Apache-2.0 grants no permission to use the name and logo "Modelen".</li>
  <li><b>Warranty:</b> Software and models are provided "as is", without warranty.</li>
</ul>
</div>
""")

NAV = [("index", "Home"), ("nasil-calisir", "How it works"), ("yol-haritasi", "Roadmap"), ("sss", "FAQ"),
       ("katil", "Join"), ("koordinatorler", "Coordinators"), ("akis", "Feed"), ("koordinator-ol", "Become a coordinator"), ("hakkinda", "About"), ("iletisim", "Contact")]
FOOT = [("gizlilik", "Privacy"), ("kvkk", "Data notice (KVKK)"), ("kullanim-sartlari", "Terms of use"),
        ("cerez", "Cookies"), ("topluluk-kurallari", "Community rules"), ("gonullu-sartlari", "Volunteer terms"), ("katki-sartlari", "Contribution terms"),
        ("lisans", "Licence")]
UI = dict(
    lang="en", skip="Skip to content", switch="Türkçe", draft=("<b>Draft:</b> This text must be reviewed by a lawyer before "
    "publication."),
    footer_tag="Open, community-owned AI for Turkish.",
    copyright="© 2026 Modelen Alternatif Eğitim Topluluğu",
    sitename="Modelen", nav_label="Main navigation", legal_label="Legal links",
)
