import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
    ArrowLeft, Download, Loader2, CheckCircle, AlertCircle,
    ChevronDown, ChevronUp, Layout, Settings, FileText,
    BarChart2, Table, Layers, BookOpen, Database
} from 'lucide-react';

// ─── Tiny UI helpers ──────────────────────────────────────────────────────────

const Label = ({ children }) => (
    <label className="block text-sm font-semibold text-gray-700 mb-1.5">{children}</label>
);

const Inp = ({ className = '', ...p }) => (
    <input className={`w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-800
      focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
      bg-white shadow-sm transition ${className}`} {...p} />
);

const Sel = ({ children, ...p }) => (
    <select className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-800
      focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
      bg-white shadow-sm transition" {...p}>{children}</select>
);

const Section = ({ title, icon: Icon, children, defaultOpen = true }) => {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <button type="button" onClick={() => setOpen(o => !o)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-violet-50 rounded-lg flex items-center justify-center">
                        <Icon className="w-4 h-4 text-violet-600" />
                    </div>
                    <span className="font-semibold text-gray-900 text-sm">{title}</span>
                </div>
                {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                        <div className="px-6 pb-6 space-y-4 border-t border-gray-50 pt-4">{children}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// ─── Slide-type icon ──────────────────────────────────────────────────────────

const SlideIcon = ({ type, hasChart, hasTable }) => {
    if (hasChart) return <BarChart2 className="w-3.5 h-3.5 text-violet-500" />;
    if (hasTable) return <Table className="w-3.5 h-3.5 text-indigo-500" />;
    const t = (type || '').toLowerCase();
    if (t.includes('title') || t.includes('cover')) return <Layout className="w-3.5 h-3.5 text-gray-400" />;
    return <FileText className="w-3.5 h-3.5 text-gray-400" />;
};

// ─── Main component ───────────────────────────────────────────────────────────

export default function PPTDBGeneratorDashboard() {
    const today = new Date().toISOString().split('T')[0];

    // form
    const [rawInput, setRawInput]         = useState('');
    const [instructions, setInstructions] = useState('');
    const [template, setTemplate]         = useState('light_red');
    const [owner, setOwner]               = useState('');
    const [email, setEmail]               = useState('');
    const [dept, setDept]                 = useState('');
    const [version, setVersion]           = useState('1.0');
    const [classif, setClassif]           = useState('Internal');
    const [approvedBy, setApprovedBy]     = useState('');
    const [creationDate, setCreationDate] = useState(today);

    // session / result
    const [sessionId, setSessionId]               = useState(null);
    const [lastProcessedInput, setLastProcessedInput] = useState(''); // mirrors app.py logic
    const [isRunning, setIsRunning]               = useState(false);
    const [error, setError]                       = useState('');
    const [downloadToken, setDownloadToken]       = useState('');
    const [slideCount, setSlideCount]             = useState(0);
    const [warning, setWarning]                   = useState('');
    const [outline, setOutline]                   = useState([]);
    const [isUpdate, setIsUpdate]                 = useState(false);
    const [expandedSlide, setExpandedSlide]       = useState(null);

    const hasResult = !!downloadToken;

    // ── Submit ───────────────────────────────────────────────────────────────
    const handleGenerate = async (e) => {
        e.preventDefault();
        setError('');
        setDownloadToken('');
        setWarning('');
        setSlideCount(0);
        setOutline([]);
        setExpandedSlide(null);

        const trimmed = rawInput.trim();
        setIsRunning(true);

        // ── Session logic mirroring app.py ──────────────────────────────────
        // Any change in input (even 1 char) = new session (new topic)
        // Same input = reuse session (update/refinement)
        let activeSessionId = sessionId;
        if (trimmed !== lastProcessedInput) {
            // New topic: reset session so backend starts fresh
            activeSessionId = null;
            setSessionId(null);
            setLastProcessedInput(trimmed);
            setIsUpdate(false);
        } else {
            // Same topic: keep session so backend refines existing PPT
            setIsUpdate(true);
        }

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const body = {
                raw_input: trimmed,
                user_instructions: instructions.trim(),
                template_name: template,
                session_id: activeSessionId || undefined,
                document_metadata: {
                    owner, email, department: dept, version,
                    classification: classif, approved_by: approvedBy,
                    creation_date: creationDate,
                },
            };

            const res = await fetch(`${apiUrl}/api/ppt-db-generator/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || 'Generation failed.');
            }

            const data = await res.json();
            setSessionId(data.session_id);
            setSlideCount(data.slide_count || 0);
            setOutline(data.outline || []);
            setDownloadToken(data.download_token);
            setWarning(data.generation_warning || '');
            setIsUpdate(data.is_update || false);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsRunning(false);
        }
    };

    const apiUrl      = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const downloadUrl = downloadToken ? `${apiUrl}/api/ppt-db-generator/download/${downloadToken}` : '';

    // Button label: show mode
    const btnLabel = lastProcessedInput && rawInput.trim() === lastProcessedInput && sessionId
        ? 'Generate Presentation'
        : 'Generate from Database';

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div className="min-h-screen bg-[#f8fbff] pt-24 pb-20">
            <div className="container mx-auto px-6 max-w-5xl">

                {/* Header */}
                <div className="mb-6">
                    <Link to="/search"
                        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-violet-600 mb-4 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back to Marketplace
                    </Link>
                    <div className="flex items-start justify-between flex-wrap gap-3">
                        <div>
                            <div className="flex items-center gap-3 mb-1">
                                <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-200">
                                    <Database className="w-5 h-5 text-white" />
                                </div>
                                <h1 className="text-3xl font-bold text-gray-900">DB Presenter Agent</h1>
                            </div>
                            <p className="text-gray-500 mt-1 text-sm ml-13">
                                Describe what you want to visualise — the agent queries your PostgreSQL database and builds a complete presentation.
                            </p>
                        </div>
                        {sessionId && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-50 border border-violet-100 rounded-full text-xs text-violet-700 font-medium">
                                <Layers className="w-3.5 h-3.5" />
                                Session active — submit a new query or follow-up
                            </div>
                        )}
                    </div>
                </div>

                <form onSubmit={handleGenerate} className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* ── LEFT ── */}
                    <div className="lg:col-span-1 space-y-4">

                        <Section title="Presentation Template" icon={Layout}>
                            <div>
                                <Label>Select Theme</Label>
                                <Sel value={template} onChange={e => setTemplate(e.target.value)}>
                                    <option value="light_red">Light Red</option>
                                    <option value="light_blue">Light Blue</option>
                                    <option value="clean_minimal">Clean Minimal</option>
                                </Sel>
                                <div className="flex gap-2 mt-3">
                                    {[
                                        { id: 'light_red',    color: 'bg-red-400',   label: 'Red' },
                                        { id: 'light_blue',   color: 'bg-blue-400',  label: 'Blue' },
                                        { id: 'clean_minimal',color: 'bg-gray-300',  label: 'Minimal' },
                                    ].map(t => (
                                        <button key={t.id} type="button" onClick={() => setTemplate(t.id)}
                                            className={`flex-1 rounded-xl border-2 py-2 flex flex-col items-center gap-1 transition-all text-xs font-medium
                                                ${template === t.id
                                                    ? 'border-violet-500 bg-violet-50 text-violet-700'
                                                    : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                                            <div className={`w-6 h-6 rounded-full ${t.color}`} />
                                            {t.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </Section>

                        <Section title="Document Metadata" icon={Settings} defaultOpen={false}>
                            <div className="grid grid-cols-1 gap-3">
                                {[
                                    { label: 'Document Owner *', value: owner,      setter: setOwner,      placeholder: 'e.g. AI Agent' },
                                    { label: 'Contact Email *',  value: email,      setter: setEmail,      placeholder: 'ai@company.com', type: 'email' },
                                    { label: 'Department *',     value: dept,       setter: setDept,       placeholder: 'e.g. Analytics' },
                                    { label: 'Version *',        value: version,    setter: setVersion,    placeholder: '1.0' },
                                    { label: 'Approved By *',    value: approvedBy, setter: setApprovedBy, placeholder: 'e.g. Management' },
                                ].map(({ label, value, setter, placeholder, type = 'text' }) => (
                                    <div key={label}>
                                        <Label>{label}</Label>
                                        <Inp type={type} value={value} onChange={e => setter(e.target.value)}
                                            placeholder={placeholder} required />
                                    </div>
                                ))}
                                <div>
                                    <Label>Classification *</Label>
                                    <Sel value={classif} onChange={e => setClassif(e.target.value)} required>
                                        <option>Internal</option>
                                        <option>Confidential</option>
                                        <option>Public</option>
                                    </Sel>
                                </div>
                                <div>
                                    <Label>Creation Date</Label>
                                    <Inp type="date" value={creationDate} onChange={e => setCreationDate(e.target.value)} />
                                </div>
                            </div>
                        </Section>

                        {/* DB info panel */}
                        <div className="bg-gradient-to-br from-violet-50 to-indigo-50 rounded-2xl border border-violet-100 p-4">
                            <div className="flex items-center gap-2 mb-2">
                                <Database className="w-4 h-4 text-violet-600" />
                                <span className="text-sm font-semibold text-violet-800">How It Works</span>
                            </div>
                            <ol className="text-xs text-violet-700 space-y-1.5 list-decimal list-inside leading-relaxed">
                                <li>Agent reads your DB schema</li>
                                <li>AI generates targeted SQL queries</li>
                                <li>Results are analysed &amp; planned into slides</li>
                                <li>Charts, tables &amp; text are built in PPTX</li>
                            </ol>
                        </div>
                    </div>

                    {/* ── RIGHT ── */}
                    <div className="lg:col-span-2 space-y-4">

                        <Section title="Natural Language Database Query" icon={Database}>
                            <div>
                                <Label>Describe what you want to analyse *</Label>
                                <textarea
                                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800
                                        focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                                        bg-white shadow-sm resize-none transition"
                                    rows={6}
                                    placeholder={
                                        `Examples:\n` +
                                        `• "Show workflow execution summary by organization"\n` +
                                        `• "Top 10 users by activity in the last 30 days"\n` +
                                        `• "Breakdown of execution statuses and failure rates"\n` +
                                        `• "Agent performance metrics across all tenants"`
                                    }
                                    value={rawInput}
                                    onChange={e => setRawInput(e.target.value)}
                                    required
                                />
                                <p className="text-xs text-gray-400 mt-1.5">
                                    Write your question in plain English. The agent will find the relevant tables and generate SQL automatically.
                                </p>
                            </div>

                            <div>
                                <Label>Additional Instructions (Optional)</Label>
                                <textarea
                                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800
                                        focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                                        bg-white shadow-sm resize-none transition"
                                    rows={2}
                                    placeholder='e.g. "Keep it to 6 slides", "Emphasise trends", "Add an executive summary slide"'
                                    value={instructions}
                                    onChange={e => setInstructions(e.target.value)}
                                />
                            </div>

                            {!isRunning && (
                                <button type="submit"
                                    className="w-full py-3.5 bg-gradient-to-r from-violet-600 to-indigo-600
                                        text-white font-bold rounded-xl shadow-lg shadow-violet-200
                                        hover:shadow-xl transition-all active:scale-95 flex items-center justify-center gap-2">
                                    <Database className="w-5 h-5" />
                                    {btnLabel}
                                </button>
                            )}
                        </Section>

                        {/* Simple loader */}
                        <AnimatePresence>
                            {isRunning && (
                                <motion.div key="loader"
                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                                    className="bg-white rounded-2xl border border-gray-100 shadow-sm p-10 flex flex-col items-center gap-4">
                                    <Loader2 className="w-12 h-12 text-violet-600 animate-spin" />
                                    <p className="text-gray-700 font-semibold text-sm">
                                        {isUpdate ? 'Generating your presentation…' : 'Querying database and building presentation…'}
                                    </p>
                                    <p className="text-xs text-gray-400 text-center">
                                        This may take 1–3 minutes.
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Error */}
                        <AnimatePresence>
                            {error && (
                                <motion.div key="error"
                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                    className="bg-red-50 border border-red-100 rounded-2xl p-5 flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
                                    <div>
                                        <p className="font-semibold text-red-700">Generation Failed</p>
                                        <p className="text-sm text-red-600 mt-1">{error}</p>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Success: Download + Outline */}
                        <AnimatePresence>
                            {hasResult && (
                                <motion.div key="success"
                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                    className="space-y-4">

                                    {/* Banner + Download */}
                                    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
                                        <div className={`flex items-start gap-3 p-4 rounded-xl border
                                            ${isUpdate ? 'bg-violet-50 border-violet-100' : 'bg-green-50 border-green-100'}`}>
                                            <CheckCircle className={`w-5 h-5 mt-0.5 shrink-0
                                                ${isUpdate ? 'text-violet-600' : 'text-green-600'}`} />
                                            <div>
                                                <p className={`font-bold ${isUpdate ? 'text-violet-800' : 'text-green-800'}`}>
                                                    {isUpdate ? 'Presentation Ready!' : 'Presentation Ready!'}
                                                </p>
                                                {slideCount > 0 && (
                                                    <p className={`text-sm mt-0.5 ${isUpdate ? 'text-violet-700' : 'text-green-700'}`}>
                                                        {slideCount} slides generated from database data.
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        {warning && (
                                            <div className="p-3 bg-yellow-50 border border-yellow-100 rounded-xl text-sm text-yellow-700">
                                                ⚠️ {warning}
                                            </div>
                                        )}

                                        <a href={downloadUrl} download="DBPresenter_Output.pptx"
                                            className="w-full flex items-center justify-center gap-2 py-3
                                                bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold
                                                rounded-xl shadow-lg shadow-violet-200 hover:shadow-xl transition-all active:scale-95">
                                            <Download className="w-5 h-5" />
                                            Download PowerPoint
                                        </a>
                                    </div>

                                    {/* Detailed Slide Outline */}
                                    {outline.length > 0 && (
                                        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                                            <div className="px-6 py-4 border-b border-gray-50 flex items-center gap-3">
                                                <div className="w-8 h-8 bg-violet-50 rounded-lg flex items-center justify-center">
                                                    <BookOpen className="w-4 h-4 text-violet-600" />
                                                </div>
                                                <div>
                                                    <span className="font-semibold text-gray-900 text-sm">
                                                        Presentation Outline
                                                    </span>
                                                    <span className="ml-2 text-xs text-gray-400">{outline.length} slides</span>
                                                </div>
                                            </div>

                                            <ul className="divide-y divide-gray-50">
                                                {outline.map((slide) => (
                                                    <li key={slide.index} className="group">
                                                        {/* Slide header row — click to expand */}
                                                        <button
                                                            type="button"
                                                            onClick={() => setExpandedSlide(
                                                                expandedSlide === slide.index ? null : slide.index
                                                            )}
                                                            className="w-full flex items-start gap-3 px-6 py-3.5
                                                                hover:bg-gray-50 transition-colors text-left">
                                                            <span className="text-xs font-mono text-gray-400 w-6 shrink-0 mt-0.5 text-right">
                                                                {slide.index}
                                                            </span>
                                                            <div className="mt-0.5 shrink-0">
                                                                <SlideIcon type={slide.type} hasChart={slide.has_chart} hasTable={slide.has_table} />
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="text-sm font-semibold text-gray-800 truncate">
                                                                    {slide.title}
                                                                </p>
                                                                {(slide.has_chart || slide.has_table) && (
                                                                    <p className="text-xs text-gray-400 mt-0.5">
                                                                        {slide.has_chart && 'Chart'}
                                                                        {slide.has_chart && slide.has_table && ' · '}
                                                                        {slide.has_table && 'Table'}
                                                                    </p>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-2 shrink-0">
                                                                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full capitalize">
                                                                    {(slide.type || 'content').replace(/_/g, ' ')}
                                                                </span>
                                                                {slide.content && (
                                                                    expandedSlide === slide.index
                                                                        ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
                                                                        : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                                                                )}
                                                            </div>
                                                        </button>

                                                        {/* Expandable content / speaker notes */}
                                                        <AnimatePresence initial={false}>
                                                            {expandedSlide === slide.index && slide.content && (
                                                                <motion.div
                                                                    initial={{ height: 0, opacity: 0 }}
                                                                    animate={{ height: 'auto', opacity: 1 }}
                                                                    exit={{ height: 0, opacity: 0 }}
                                                                    transition={{ duration: 0.18 }}
                                                                    className="overflow-hidden">
                                                                    <div className="mx-6 mb-4 p-4 bg-violet-50 rounded-xl border border-violet-100">
                                                                        <p className="text-xs font-semibold text-violet-600 mb-2 flex items-center gap-1.5">
                                                                            <BookOpen className="w-3.5 h-3.5" />
                                                                            Slide Content &amp; Speaker Notes
                                                                        </p>
                                                                        <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                                                                            {slide.content}
                                                                        </p>
                                                                    </div>
                                                                </motion.div>
                                                            )}
                                                        </AnimatePresence>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>

                    </div>
                </form>
            </div>
        </div>
    );
}
