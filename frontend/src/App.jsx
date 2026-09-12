import { useEffect, useRef, useState } from "react";
import { TRANSLATIONS } from "./translations";

const API_BASE = import.meta.env.VITE_API_URL || "";

const LANGUAGES = [
  { code: "en-IN", label: "English" },
  { code: "hi-IN", label: "हिंदी (Hindi)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
  { code: "te-IN", label: "తెలుగు (Telugu)" },
  { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ml-IN", label: "മലയാളം (Malayalam)" },
  { code: "mr-IN", label: "मराठी (Marathi)" },
  { code: "bn-IN", label: "বাংলা (Bengali)" },
];

const CATEGORIES = [
  { id: "all", labelKey: "categoryAll", defaultLabel: "All Schemes", icon: "🇮🇳" },
  { id: "agriculture", labelKey: "categoryAgri", defaultLabel: "🌾 Agriculture", icon: "🌾" },
  { id: "health", labelKey: "categoryHealth", defaultLabel: "🏥 Health & Medical", icon: "🏥" },
  { id: "housing", labelKey: "categoryHousing", defaultLabel: "🏠 Housing & Energy", icon: "🏠" },
  { id: "education", labelKey: "categoryEdu", defaultLabel: "🎓 Education & Youth", icon: "🎓" },
  { id: "girl_child_welfare", labelKey: "categoryWomen", defaultLabel: "👧 Women & Children", icon: "👧" },
  { id: "artisan_welfare", labelKey: "categoryArtisan", defaultLabel: "🔨 Artisans & Vendors", icon: "🔨" },
  { id: "pension", labelKey: "categoryPension", defaultLabel: "🛡️ Pension & Security", icon: "🛡️" },
];

function useSpeechRecognition(lang) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = lang;

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    return () => {
      try {
        recognition.abort();
      } catch (e) {}
    };
  }, [lang]);

  const start = () => {
    if (!recognitionRef.current) return;
    setTranscript("");
    setListening(true);
    try {
      recognitionRef.current.start();
    } catch (e) {
      setListening(false);
    }
  };

  const stop = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {}
    setListening(false);
  };

  return { listening, transcript, supported, start, stop, setTranscript };
}

export default function App() {
  const [phone, setPhone] = useState("");
  const [language, setLanguage] = useState("hi-IN");
  const [manualText, setManualText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [draft, setDraft] = useState(null);
  const [draftSchemeName, setDraftSchemeName] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);

  // Accessibility Font Scaling
  const [fontScale, setFontScale] = useState("normal"); // 'normal' | 'large' | 'xlarge'

  // Filtering & Search
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Document Readiness Tracker: { [schemeId]: Set of doc names }
  const [checkedDocs, setCheckedDocs] = useState({});

  // Active translation dictionary
  const t = TRANSLATIONS[language] || TRANSLATIONS["en-IN"];

  // Follow-up interaction state
  const [followup, setFollowup] = useState(null);
  const [followupAnswer, setFollowupAnswer] = useState("");
  const [followupLoading, setFollowupLoading] = useState(false);

  // Transparency panel expansion tracking
  const [expandedSchemes, setExpandedSchemes] = useState({});

  // Voice output (SpeechSynthesis)
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingSchemeId, setSpeakingSchemeId] = useState(null);

  // Impact stats modal
  const [statsModal, setStatsModal] = useState(false);
  const [statsData, setStatsData] = useState(null);

  // Conversational AI Assistant Drawer / State
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: "assistant",
      text: language === "hi-IN"
        ? "नमस्ते! मैं आपका सिविकवॉइस एआई सहायक हूं। आप मुझसे योजनाओं, आवश्यक दस्तावेजों या आवेदन प्रक्रिया के बारे में कुछ भी पूछ सकते हैं।"
        : "Namaste! I am your CivicVoice Assistant. Feel free to ask me anything about your eligible schemes, required documents, or application procedures."
    }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Toast notification
  const [toastMessage, setToastMessage] = useState("");

  // Speech hooks
  const { listening, transcript, supported, start } = useSpeechRecognition(language);
  const followupSpeech = useSpeechRecognition(language);
  const chatSpeech = useSpeechRecognition(language);

  useEffect(() => {
    if (transcript) {
      setManualText((prev) => (prev ? `${prev} ${transcript}` : transcript));
    }
  }, [transcript]);

  useEffect(() => {
    if (followupSpeech.transcript) {
      setFollowupAnswer(followupSpeech.transcript);
    }
  }, [followupSpeech.transcript]);

  useEffect(() => {
    if (chatSpeech.transcript) {
      setChatInput(chatSpeech.transcript);
    }
  }, [chatSpeech.transcript]);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) {
        const data = await res.json();
        setStatsData(data);
      }
    } catch (e) {}
  }

  function showToast(msg) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(""), 3500);
  }

  function handlePreset(p) {
    setPhone(p.phone);
    setManualText(p.text);
    setError("");
    setResult(null);
    setDraft(null);
    setFollowup(null);
    setCheckedDocs({});
  }

  async function submitProcess(phoneNum, textToProcess) {
    if (!phoneNum.trim() || !textToProcess.trim()) {
      setError(language === "hi-IN" ? "कृपया मोबाइल नंबर और अपनी स्थिति दर्ज करें।" : "Please enter a valid phone number and describe your situation.");
      return;
    }
    setError("");
    setLoading(true);
    setDraft(null);
    stopSpeaking();

    try {
      const res = await fetch(`${API_BASE}/api/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phoneNum.trim(), text: textToProcess.trim() }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setResult(data);
      loadStats();

      // Check if there are "possible" schemes and fetch proactive follow-up
      const hasPossible = data.matched_schemes.some((s) => s.status === "possible");
      if (hasPossible) {
        fetchFollowup(phoneNum.trim(), language);
      } else {
        setFollowup(null);
      }
    } catch (err) {
      setError("Couldn't reach CivicVoice backend. Ensure server is running at http://localhost:8000.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchFollowup(phoneNum, lang) {
    try {
      setFollowupLoading(true);
      const res = await fetch(`${API_BASE}/api/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phoneNum, target_lang: lang }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.has_followup) {
          setFollowup(data);
          setFollowupAnswer("");
        } else {
          setFollowup(null);
        }
      }
    } catch (e) {
    } finally {
      setFollowupLoading(false);
    }
  }

  async function handleFollowupSubmit(answerText) {
    const ans = (answerText || followupAnswer).trim();
    if (!ans) return;
    setFollowupAnswer("");
    await submitProcess(phone, ans);
  }

  function toggleBreakdown(schemeId) {
    setExpandedSchemes((prev) => ({
      ...prev,
      [schemeId]: !prev[schemeId],
    }));
  }

  function handleDocToggle(schemeId, docName) {
    setCheckedDocs((prev) => {
      const current = prev[schemeId] || [];
      const updated = current.includes(docName)
        ? current.filter((d) => d !== docName)
        : [...current, docName];
      return { ...prev, [schemeId]: updated };
    });
  }

  async function handleDraftText(schemeId) {
    setDraftLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), scheme_id: schemeId }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setDraft(data.draft_text);
      setDraftSchemeName(data.scheme_name || "Application Form");
    } catch (err) {
      setError("Couldn't generate text draft. Please try again.");
    } finally {
      setDraftLoading(false);
    }
  }

  function handlePdfDownload(schemeId) {
    const url = `${API_BASE}/api/draft/pdf?phone=${encodeURIComponent(phone.trim())}&scheme_id=${encodeURIComponent(schemeId)}`;
    window.open(url, "_blank");
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setSpeakingSchemeId(null);
  }

  async function speakText(textToSpeak, schemeId = null) {
    if (!("speechSynthesis" in window)) {
      alert("Speech synthesis is not supported in your browser.");
      return;
    }

    if (isSpeaking && speakingSchemeId === schemeId) {
      stopSpeaking();
      return;
    }

    stopSpeaking();

    let finalText = textToSpeak;
    if (!language.startsWith("en")) {
      try {
        const res = await fetch(`${API_BASE}/api/translate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: textToSpeak, target_lang: language }),
        });
        if (res.ok) {
          const trans = await res.json();
          finalText = trans.translated_text || textToSpeak;
        }
      } catch (e) {}
    }

    const utterance = new SpeechSynthesisUtterance(finalText);
    utterance.lang = language;
    utterance.rate = 0.92;

    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) => v.lang.startsWith(language.split("-")[0]));
    if (matchedVoice) utterance.voice = matchedVoice;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setSpeakingSchemeId(schemeId);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setSpeakingSchemeId(null);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setSpeakingSchemeId(null);
    };

    window.speechSynthesis.speak(utterance);
  }

  async function handlePlayAdvisorBriefing() {
    if (!phone) return;
    try {
      const res = await fetch(`${API_BASE}/api/advisor-summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), language }),
      });
      if (res.ok) {
        const data = await res.json();
        speakText(data.summary_text, "advisor-briefing");
      }
    } catch (e) {}
  }

  async function handleSendChat(query) {
    const textToSend = (query || chatInput).trim();
    if (!textToSend) return;

    setChatMessages((prev) => [...prev, { sender: "user", text: textToSend }]);
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: phone.trim() || "guest",
          message: textToSend,
          language,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [...prev, { sender: "assistant", text: data.reply }]);
      } else {
        setChatMessages((prev) => [
          ...prev,
          { sender: "assistant", text: "I'm having trouble connecting right now. Please try again in a moment." }
        ]);
      }
    } catch (e) {
      setChatMessages((prev) => [
        ...prev,
        { sender: "assistant", text: "Network error connecting to assistant service." }
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  function handleShareWhatsApp() {
    if (!result) return;
    const confirmed = result.matched_schemes.filter((s) => s.status === "confirmed");
    const totalVal = confirmed.reduce((sum, s) => sum + (s.benefit_value_inr || 0), 0);
    const names = confirmed.map((s, i) => `${i + 1}. *${s.name}* (Benefit: ${s.benefit})`).join("\n");

    const message = `🏛️ *CivicVoice Citizen Welfare Discovery Report*\n\n` +
      `👤 *Citizen:* +91 ${phone}\n` +
      `✅ *Confirmed Eligible Schemes:* ${confirmed.length}\n` +
      `💰 *Total Estimated Benefit:* ₹${totalVal.toLocaleString('en-IN')}\n\n` +
      `*Eligible Programs:*\n${names}\n\n` +
      `Generated via CivicVoice AI — https://civicvoice.gov.in`;

    const encoded = encodeURIComponent(message);
    window.open(`https://api.whatsapp.com/send?text=${encoded}`, "_blank");
  }

  function handleCopySummary() {
    if (!result) return;
    const confirmed = result.matched_schemes.filter((s) => s.status === "confirmed");
    const totalVal = confirmed.reduce((sum, s) => sum + (s.benefit_value_inr || 0), 0);
    const names = confirmed.map((s, i) => `${i + 1}. ${s.name}`).join("\n");

    const summary = `CivicVoice Welfare Summary for +91 ${phone}\n` +
      `Confirmed Schemes: ${confirmed.length}\n` +
      `Total Potential Benefits: ₹${totalVal.toLocaleString('en-IN')}\n\n` +
      `Schemes:\n${names}\n\nGenerated via CivicVoice.`;

    navigator.clipboard.writeText(summary).then(() => {
      showToast(t.copiedToast || "Summary copied to clipboard!");
    });
  }

  // Filter matched schemes by Category, Status, and Search Query
  const filteredSchemes = (result?.matched_schemes || []).filter((scheme) => {
    // 1. Category Filter
    if (selectedCategory !== "all") {
      if (selectedCategory === "agriculture" && !scheme.category.includes("agriculture")) return false;
      if (selectedCategory === "health" && scheme.category !== "health") return false;
      if (selectedCategory === "housing" && !["housing", "renewable_energy", "energy_lpg"].includes(scheme.category)) return false;
      if (selectedCategory === "education" && scheme.category !== "education") return false;
      if (selectedCategory === "girl_child_welfare" && !["girl_child_welfare", "maternity_welfare"].includes(scheme.category)) return false;
      if (selectedCategory === "artisan_welfare" && !["artisan_welfare", "urban_livelihood", "micro_enterprise"].includes(scheme.category)) return false;
      if (selectedCategory === "pension" && !["pension", "disability_welfare", "social_welfare", "insurance", "social_security", "food_security"].includes(scheme.category)) return false;
    }

    // 2. Status Filter
    if (statusFilter !== "all" && scheme.status !== statusFilter) return false;

    // 3. Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inName = scheme.name.toLowerCase().includes(q);
      const inBenefit = scheme.benefit.toLowerCase().includes(q);
      const inClause = scheme.clause.toLowerCase().includes(q);
      const inDocs = scheme.apply_docs.some((d) => d.toLowerCase().includes(q));
      if (!inName && !inBenefit && !inClause && !inDocs) return false;
    }

    return true;
  });

  // Calculate Entitlements
  const confirmedSchemes = (result?.matched_schemes || []).filter((s) => s.status === "confirmed");
  const possibleSchemes = (result?.matched_schemes || []).filter((s) => s.status === "possible");
  const totalConfirmedINR = confirmedSchemes.reduce((sum, s) => sum + (s.benefit_value_inr || 0), 0);
  const totalConfirmedLakhs = (totalConfirmedINR / 100000).toFixed(2);

  return (
    <div className={`civic-app scale-${fontScale}`}>
      {/* Toast Notification */}
      {toastMessage && <div className="floating-toast">{toastMessage}</div>}

      {/* Top Civic Navigation Bar */}
      <nav className="civic-nav">
        <div className="nav-container">
          <div className="brand">
            <div className="emblem">🏛️</div>
            <div>
              <span className="brand-title">CivicVoice</span>
              <span className="brand-badge">{t.brandSubtitle}</span>
            </div>
          </div>

          <div className="nav-actions">
            {/* Font Size Accessibility Scaler */}
            <div className="font-scale-control" title={t.textSize || "Text Size"}>
              <button
                type="button"
                className={`font-btn ${fontScale === "normal" ? "active" : ""}`}
                onClick={() => setFontScale("normal")}
              >
                A
              </button>
              <button
                type="button"
                className={`font-btn lg ${fontScale === "large" ? "active" : ""}`}
                onClick={() => setFontScale("large")}
              >
                A+
              </button>
              <button
                type="button"
                className={`font-btn xlg ${fontScale === "xlarge" ? "active" : ""}`}
                onClick={() => setFontScale("xlarge")}
              >
                A++
              </button>
            </div>

            {/* Global Language Selector */}
            <div className="lang-switcher-nav">
              <span className="globe-icon">🌐</span>
              <select
                className="lang-select-nav"
                value={language}
                onChange={(e) => {
                  setLanguage(e.target.value);
                  if (result && phone) {
                    fetchFollowup(phone, e.target.value);
                  }
                }}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* AI Assistant Toggle Button */}
            <button
              type="button"
              className={`chat-toggle-nav-btn ${chatOpen ? "active" : ""}`}
              onClick={() => setChatOpen(!chatOpen)}
              title="Open Citizen AI Assistant"
            >
              💬 AI Assistant
            </button>

            {/* Impact Dashboard Button */}
            <button
              type="button"
              className="stats-badge-btn"
              onClick={() => {
                loadStats();
                setStatsModal(true);
              }}
            >
              📊 {t.impactStats}
              {statsData && statsData.total_confirmed_matches > 0 && (
                <span className="stats-pill">
                  {statsData.total_confirmed_matches} · ₹{statsData.total_estimated_welfare_lakhs}L+
                </span>
              )}
            </button>
          </div>
        </div>
      </nav>

      <main className="page-main">
        {/* Hero Section */}
        <header className="hero-section">
          <div className="hero-pill">
            <span>🇮🇳</span> {t.heroPill}
          </div>
          <h1 className="hero-heading">
            {t.heroHeading1} <br />
            <span>{t.heroHeading2}</span>
          </h1>
          <p className="hero-sub">{t.heroSub}</p>

          {/* Presets in Selected Language */}
          <div className="preset-container">
            <span className="preset-label">{t.demoProfilesLabel}</span>
            <div className="preset-pills">
              {t.presets.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="preset-btn"
                  onClick={() => handlePreset(p)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Input Panel */}
        <section className="civic-card main-panel">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitProcess(phone, manualText);
            }}
          >
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="phone-input">
                  <span>📱 {t.phoneLabel}</span>
                  <span className="field-hint">{t.phoneHint}</span>
                </label>
                <input
                  id="phone-input"
                  type="tel"
                  placeholder={t.phonePlaceholder}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="lang-select">
                  <span>🗣️ {t.langLabel}</span>
                  <span className="field-hint">{t.langHint}</span>
                </label>
                <select
                  id="lang-select"
                  value={language}
                  onChange={(e) => {
                    setLanguage(e.target.value);
                    if (result && phone) {
                      fetchFollowup(phone, e.target.value);
                    }
                  }}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group full-width">
              <label htmlFor="situation-text">
                <span>📝 {t.situationLabel}</span>
                <span className="field-hint">{t.situationHint}</span>
              </label>
              <textarea
                id="situation-text"
                rows={4}
                placeholder={t.situationPlaceholder}
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                required
              />
            </div>

            <div className="action-row">
              <div className="mic-wrapper">
                {supported ? (
                  <button
                    type="button"
                    className={`mic-button ${listening ? "is-listening" : ""}`}
                    onClick={listening ? () => {} : start}
                  >
                    <span className="mic-icon">{listening ? "🔴" : "🎙️"}</span>
                    <span>{listening ? t.listeningBtn : t.speakBtn}</span>
                  </button>
                ) : (
                  <span className="unsupported-hint">Voice input available on Chrome/Edge.</span>
                )}
                {listening && <span className="pulse-indicator"></span>}
              </div>

              <button
                type="submit"
                className="submit-btn"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span> {t.checkingBtn}
                  </>
                ) : (
                  t.checkBtn
                )}
              </button>
            </div>

            {error && <div className="alert-box error-alert">{error}</div>}
          </form>
        </section>

        {/* Proactive Follow-up Clarification Banner */}
        {followup && (
          <section className="civic-card followup-card">
            <div className="followup-header">
              <span className="followup-icon">💡</span>
              <div>
                <h3 className="followup-title">{t.followupTitle}</h3>
                <p className="followup-subtitle">
                  {t.followupSub(followup.potential_unlocks_count, followup.affected_schemes.join(", "))}
                </p>
              </div>
            </div>

            <div className="followup-question-box">
              <p className="followup-question-text">"{followup.question}"</p>
              <button
                type="button"
                className="listen-question-btn"
                onClick={() => speakText(followup.question, "followup")}
              >
                {isSpeaking && speakingSchemeId === "followup" ? t.stopBtn : t.listenBtn}
              </button>
            </div>

            {/* Quick Answer Option Chips */}
            {followup.options && followup.options.length > 0 && (
              <div className="options-container">
                <span className="options-label">{t.quickSelectLabel}</span>
                <div className="options-chips">
                  {followup.options.map((opt, i) => (
                    <button
                      key={i}
                      type="button"
                      className="option-chip"
                      onClick={() => handleFollowupSubmit(opt)}
                      disabled={loading}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Follow-up Voice / Text Input */}
            <div className="followup-input-row">
              <input
                type="text"
                placeholder={t.situationHint}
                value={followupAnswer}
                onChange={(e) => setFollowupAnswer(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleFollowupSubmit()}
              />
              {followupSpeech.supported && (
                <button
                  type="button"
                  className={`mic-sm-btn ${followupSpeech.listening ? "active" : ""}`}
                  onClick={followupSpeech.listening ? followupSpeech.stop : followupSpeech.start}
                  title="Speak answer"
                >
                  🎙️
                </button>
              )}
              <button
                type="button"
                className="followup-submit-btn"
                onClick={() => handleFollowupSubmit()}
                disabled={loading || !followupAnswer.trim()}
              >
                {t.submitDetailBtn}
              </button>
            </div>
          </section>
        )}

        {/* Results Section */}
        {result && (
          <section className="results-wrapper">
            {/* Returning Citizen Persistent Memory Banner */}
            {result.is_returning_citizen && (
              <div className="memory-banner">
                <span className="memory-icon">🧠</span>
                <div>
                  <strong>{t.memoryBannerTitle}</strong> {t.memoryBannerSub}
                  <div className="memory-facts">
                    {Object.entries(result.profile)
                      .filter(([k, v]) => v && k !== "raw_situation_summary")
                      .map(([k, v]) => (
                        <span key={k} className="fact-pill">
                          {k.replace(/_/g, " ")}: <strong>{String(v)}</strong>
                        </span>
                      ))}
                  </div>
                </div>
              </div>
            )}

            {/* Welfare Entitlement Meter & AI Engine Banner */}
            <div className="entitlement-banner">
              <div className="entitlement-left">
                <div className="entitlement-badge">
                  <span className="star-icon">✨</span>
                  <span>{result.extraction_source || t.aiEngineBadge || "AI Extraction Active"}</span>
                </div>
                <h3 className="entitlement-amount">
                  ₹{totalConfirmedINR.toLocaleString("en-IN")}{" "}
                  <span className="amount-sub">
                    ({totalConfirmedLakhs} Lakhs INR)
                  </span>
                </h3>
                <p className="entitlement-desc">
                  {t.welfarePotentialTitle}: {confirmedSchemes.length} schemes confirmed eligible,{" "}
                  {possibleSchemes.length} pending additional verification.
                </p>
              </div>

              <div className="entitlement-actions">
                <button
                  type="button"
                  className="advisor-brief-btn"
                  onClick={handlePlayAdvisorBriefing}
                >
                  {isSpeaking && speakingSchemeId === "advisor-briefing"
                    ? (t.advisorBriefingStop || "⏹️ Stop Briefing")
                    : (t.advisorBriefingBtn || "🎙️ Listen to AI Advisor Briefing")}
                </button>

                <div className="share-buttons-row">
                  <button
                    type="button"
                    className="whatsapp-btn"
                    onClick={handleShareWhatsApp}
                    title="Share report on WhatsApp"
                  >
                    {t.shareWhatsApp || "📱 Share on WhatsApp"}
                  </button>
                  <button
                    type="button"
                    className="copy-summary-btn"
                    onClick={handleCopySummary}
                    title="Copy text summary"
                  >
                    {t.copySummary || "📋 Copy Summary"}
                  </button>
                </div>
              </div>
            </div>

            {/* Filter & Search Toolbar */}
            <div className="toolbar-card">
              <div className="search-bar-wrap">
                <span className="search-icon">🔍</span>
                <input
                  type="text"
                  className="search-input"
                  placeholder={t.searchPlaceholder || "Search schemes, benefits, documents..."}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="clear-search-btn"
                    onClick={() => setSearchQuery("")}
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Status Toggle Pills */}
              <div className="status-filter-pills">
                <button
                  type="button"
                  className={`status-pill-btn ${statusFilter === "all" ? "active" : ""}`}
                  onClick={() => setStatusFilter("all")}
                >
                  {t.filterStatusAll || "All"} ({result.matched_schemes.length})
                </button>
                <button
                  type="button"
                  className={`status-pill-btn confirmed ${statusFilter === "confirmed" ? "active" : ""}`}
                  onClick={() => setStatusFilter("confirmed")}
                >
                  ✓ {t.filterStatusConfirmed || "Confirmed"} ({confirmedSchemes.length})
                </button>
                <button
                  type="button"
                  className={`status-pill-btn possible ${statusFilter === "possible" ? "active" : ""}`}
                  onClick={() => setStatusFilter("possible")}
                >
                  ⏳ {t.filterStatusPossible || "Needs Info"} ({possibleSchemes.length})
                </button>
              </div>

              {/* Category Filter Tabs */}
              <div className="category-tabs">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    className={`category-tab-btn ${selectedCategory === cat.id ? "active" : ""}`}
                    onClick={() => setSelectedCategory(cat.id)}
                  >
                    {t[cat.labelKey] || cat.defaultLabel}
                  </button>
                ))}
              </div>
            </div>

            <div className="results-header">
              <div>
                <h2>{t.resultsTitle}</h2>
                <p className="results-sub">
                  Showing {filteredSchemes.length} of {result.matched_schemes.length} schemes
                </p>
              </div>
              <div className="results-actions">
                <button
                  type="button"
                  className="read-summary-btn"
                  onClick={() => {
                    const text = `${t.resultsTitle}: ${filteredSchemes.length} schemes found, ${confirmedSchemes.length} confirmed.`;
                    speakText(text, "summary");
                  }}
                >
                  {isSpeaking && speakingSchemeId === "summary" ? t.stopAudioBtn : t.readSummaryBtn}
                </button>
              </div>
            </div>

            {filteredSchemes.length === 0 ? (
              <div className="empty-state civic-card">
                <p>{t.noSchemes}</p>
                <p className="hint">
                  {searchQuery || selectedCategory !== "all" || statusFilter !== "all"
                    ? "Try clearing your filters or search keywords."
                    : t.noSchemesHint}
                </p>
              </div>
            ) : (
              <div className="schemes-grid">
                {filteredSchemes.map((scheme) => {
                  const isConfirmed = scheme.status === "confirmed";
                  const isExpanded = expandedSchemes[scheme.id];

                  // Document Checklist Readiness
                  const docs = scheme.apply_docs || [];
                  const userDocs = checkedDocs[scheme.id] || [];
                  const readyCount = docs.filter((d) => userDocs.includes(d)).length;
                  const readinessPct = docs.length > 0 ? Math.round((readyCount / docs.length) * 100) : 0;

                  return (
                    <article
                      key={scheme.id}
                      className={`scheme-card ${isConfirmed ? "is-confirmed" : "is-possible"}`}
                    >
                      <div className="card-top">
                        <div className="category-tag">
                          {scheme.category.replace(/_/g, " ").toUpperCase()}
                        </div>
                        <div className={`status-badge ${isConfirmed ? "badge-confirmed" : "badge-possible"}`}>
                          {isConfirmed ? t.confirmedBadge : t.possibleBadge}
                        </div>
                      </div>

                      <h3 className="scheme-title">{scheme.name}</h3>

                      <div className="benefit-box">
                        <span className="benefit-icon">🎁</span>
                        <div className="benefit-text">
                          <strong>{t.benefitLabel}</strong>
                          {scheme.benefit}
                        </div>
                      </div>

                      <div className="clause-quote">
                        <span className="quote-mark">“</span>
                        <p>{scheme.clause}</p>
                      </div>

                      {/* Official Verification Portal Link */}
                      <div className="source-link-row">
                        <span className="source-label">{t.sourceLabel}</span>
                        <a
                          href={scheme.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-url"
                        >
                          {scheme.source_url} ↗
                        </a>
                      </div>

                      {/* Interactive Document Checklist & Readiness Meter */}
                      <div className="docs-checklist-box">
                        <div className="checklist-header">
                          <span className="docs-title">📋 {t.readinessTitle || "Application Documents"}:</span>
                          <span className="readiness-count">
                            {readyCount}/{docs.length} Ready ({readinessPct}%)
                          </span>
                        </div>

                        <div className="readiness-bar">
                          <div
                            className="readiness-fill"
                            style={{ width: `${readinessPct}%` }}
                          ></div>
                        </div>

                        <div className="interactive-doc-list">
                          {docs.map((doc, idx) => {
                            const isChecked = userDocs.includes(doc);
                            return (
                              <label
                                key={idx}
                                className={`interactive-doc-item ${isChecked ? "checked" : ""}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => handleDocToggle(scheme.id, doc)}
                                />
                                <span>{doc}</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {/* Transparency Breakdown Button */}
                      <div className="transparency-section">
                        <button
                          type="button"
                          className="breakdown-toggle-btn"
                          onClick={() => toggleBreakdown(scheme.id)}
                        >
                          <span>{isExpanded ? t.hideQualify : t.whyQualify}</span>
                        </button>

                        {isExpanded && (
                          <div className="breakdown-table">
                            {scheme.rule_breakdown.map((rule, idx) => {
                              const icon =
                                rule.status === "satisfied" ? "✅" : rule.status === "contradicted" ? "❌" : "⏳";
                              return (
                                <div key={idx} className={`breakdown-row status-${rule.status}`}>
                                  <span className="rule-icon">{icon}</span>
                                  <div className="rule-info">
                                    <span className="rule-label">{rule.label}</span>
                                    <span className="rule-desc">{rule.description}</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Action Bar */}
                      <div className="card-actions">
                        <button
                          type="button"
                          className="voice-read-btn"
                          onClick={() => {
                            const text = `${scheme.name}. ${t.benefitLabel} ${scheme.benefit}. ${t.docsLabel} ${scheme.apply_docs.join(", ")}`;
                            speakText(text, scheme.id);
                          }}
                        >
                          {isSpeaking && speakingSchemeId === scheme.id ? t.stopBtn : t.listenBtn}
                        </button>

                        {isConfirmed && (
                          <div className="confirmed-actions">
                            <button
                              type="button"
                              className="pdf-btn"
                              onClick={() => handlePdfDownload(scheme.id)}
                              title="Download pre-filled official application PDF form"
                            >
                              {t.downloadPdfBtn}
                            </button>
                            <button
                              type="button"
                              className="text-draft-btn"
                              onClick={() => handleDraftText(scheme.id)}
                            >
                              {t.previewDraftBtn}
                            </button>
                          </div>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* Text Draft Modal / Section */}
        {draft && (
          <section className="civic-card draft-card">
            <div className="draft-header">
              <div>
                <h2>{draftSchemeName}</h2>
                <p className="draft-sub">Pre-filled using verified facts stored in citizen memory.</p>
              </div>
              <button
                type="button"
                className="close-draft-btn"
                onClick={() => setDraft(null)}
              >
                {t.closeDraftBtn}
              </button>
            </div>
            <pre className="draft-code-block">{draft}</pre>
          </section>
        )}
      </main>

      {/* Floating AI Chat Assistant Drawer */}
      {chatOpen && (
        <div className="chat-drawer-container">
          <div className="chat-drawer">
            <div className="chat-header">
              <div className="chat-header-info">
                <span className="chat-bot-icon">🤖</span>
                <div>
                  <h4>{t.chatDrawerTitle || "CivicVoice AI Assistant"}</h4>
                  <p>{t.chatDrawerSub || "Ask about rules, documents, or procedures"}</p>
                </div>
              </div>
              <button
                type="button"
                className="chat-close-btn"
                onClick={() => setChatOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="chat-messages-box">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.sender}`}>
                  <div className="chat-bubble">{msg.text}</div>
                </div>
              ))}
              {chatLoading && (
                <div className="chat-message assistant">
                  <div className="chat-bubble thinking">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Prompt Chips */}
            <div className="chat-quick-chips">
              <button
                type="button"
                className="chat-chip"
                onClick={() => handleSendChat(t.chatQuick1 || "What documents do I need?")}
              >
                {t.chatQuick1 || "What documents do I need?"}
              </button>
              <button
                type="button"
                className="chat-chip"
                onClick={() => handleSendChat(t.chatQuick2 || "How do I apply online?")}
              >
                {t.chatQuick2 || "How do I apply online?"}
              </button>
              <button
                type="button"
                className="chat-chip"
                onClick={() => handleSendChat(t.chatQuick3 || "What is my total benefit amount?")}
              >
                {t.chatQuick3 || "What is my total benefit?"}
              </button>
            </div>

            {/* Chat Input */}
            <form
              className="chat-input-form"
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChat();
              }}
            >
              <input
                type="text"
                placeholder={t.chatPlaceholder || "Ask anything about government schemes..."}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
              />
              {chatSpeech.supported && (
                <button
                  type="button"
                  className={`chat-mic-btn ${chatSpeech.listening ? "active" : ""}`}
                  onClick={chatSpeech.listening ? chatSpeech.stop : chatSpeech.start}
                  title="Speak query"
                >
                  🎙️
                </button>
              )}
              <button
                type="submit"
                className="chat-send-btn"
                disabled={chatLoading || !chatInput.trim()}
              >
                {t.chatSendBtn || "Ask"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Aggregate Stats Modal */}
      {statsModal && statsData && (
        <div className="modal-backdrop" onClick={() => setStatsModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{t.modalTitle}</h3>
              <button
                type="button"
                className="close-modal-btn"
                onClick={() => setStatsModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-num">{statsData.total_citizens_registered}</span>
                <span className="stat-title">{t.statCitizens}</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{statsData.total_confirmed_matches}</span>
                <span className="stat-title">{t.statMatches}</span>
              </div>
              <div className="stat-box highlight">
                <span className="stat-num">₹{statsData.total_estimated_welfare_lakhs} Lakhs</span>
                <span className="stat-title">{t.statWelfare}</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{statsData.total_available_schemes}</span>
                <span className="stat-title">{t.statSchemes}</span>
              </div>
            </div>

            {statsData.top_schemes && statsData.top_schemes.length > 0 && (
              <div className="top-schemes-list">
                <h4>{t.topSchemesTitle}</h4>
                <ul>
                  {statsData.top_schemes.map((s, idx) => (
                    <li key={idx}>
                      <span>{s.name}</span>
                      <span className="count-tag">{s.count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="civic-footer">
        <div className="footer-content">
          <p>
            <strong>{t.footerTitle}</strong>
          </p>
          <p className="footer-meta">{t.footerMeta}</p>
        </div>
      </footer>
    </div>
  );
}
