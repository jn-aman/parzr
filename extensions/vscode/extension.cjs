'use strict';
const vscode = require('vscode');
const { spawn } = require('node:child_process');
const { existsSync } = require('node:fs');
const modes = ['Fix', 'Professional', 'Friendly', 'Concise', 'Direct'];
let processHandle;
const documents = new Map();
let enginePath, pending, idleTimer, output = '';
const { StringDecoder } = require('node:string_decoder');
let decoder = new StringDecoder('utf8');
let engineQueue = Promise.resolve();
const proseLanguages = ['plaintext', 'markdown', 'mdx', 'git-commit'];
function localDocument(doc) { return !vscode.env.remoteName && ['file', 'untitled'].includes(doc.uri.scheme); }
function runEngine(path, request, current = () => true) {
  const task = engineQueue.then(() => {
    if (!current()) throw new Error('The writing check was superseded.');
    return runEngineNow(path, request);
  });
  engineQueue = task.catch(() => {});
  return task;
}
function stopEngine(message) {
  clearTimeout(idleTimer);
  const child = processHandle; processHandle = undefined;
  if (pending) { clearTimeout(pending.timer); pending.reject(new Error(message)); pending = undefined; }
  child?.kill(); output = ''; decoder = new StringDecoder('utf8');
}
function runEngineNow(path, request) {
  return new Promise((resolve, reject) => {
    if (!existsSync(path)) { reject(new Error('Install Parzr in Applications, or set parzr.enginePath.')); return; }
    if (pending) { reject(new Error('Parzr is already checking a passage.')); return; }
    clearTimeout(idleTimer);
    if (processHandle && enginePath !== path) stopEngine('The writing engine changed.');
    if (!processHandle) {
      const child = spawn(path, [], { shell: false, stdio: ['pipe', 'pipe', 'ignore'] });
      processHandle = child; enginePath = path;
      child.on('error', () => { if (processHandle === child) stopEngine('The local engine could not start.'); });
      child.stdin.on('error', () => { if (processHandle === child) stopEngine('The local engine closed its input.'); });
      child.on('exit', () => { if (processHandle === child) stopEngine('The local engine stopped before returning a result.'); });
      child.stdout.on('data', chunk => {
        if (processHandle !== child) return;
        output += decoder.write(chunk);
        if (output.length > 1024 * 1024) { stopEngine('The engine response exceeded its limit.'); return; }
        if (!output.includes('\n')) return;
        const line = output.slice(0, output.indexOf('\n')); output = output.slice(output.indexOf('\n')+1);
        const item = pending; pending = undefined;
        if (!item) { stopEngine('The engine returned an unexpected response.'); return; }
        clearTimeout(item.timer);
        try { const result = JSON.parse(line); result.error ? item.reject(new Error(result.error)) : item.resolve(result); }
        catch { item.reject(new Error('The engine returned an invalid response.')); stopEngine('Invalid response.'); }
        idleTimer = setTimeout(() => { if (!pending) stopEngine('Idle connection closed.'); }, 35000);
      });
    }
    pending = {resolve, reject, timer: setTimeout(() => stopEngine('The local model timed out. Try a shorter selection.'), 25000)};
    processHandle.stdin.write(JSON.stringify(request) + '\n');
  });
}
function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection('Parzr');
  const checked = new Map();
  let checkTimer, checkGeneration = 0;
  const health = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 20);
  health.command = 'parzr.rewrite';
  function schedule() {
    clearTimeout(checkTimer); const generation = ++checkGeneration;
    const editor = vscode.window.activeTextEditor;
    if (!editor) { health.hide(); return; }
    const doc = editor.document, uri = doc.uri.toString(), configuration = vscode.workspace.getConfiguration('parzr');
    diagnostics.delete(doc.uri); checked.delete(uri); health.hide();
    if (!configuration.get('automatic', true) || !localDocument(doc) || !proseLanguages.includes(doc.languageId)) return;
    const version = doc.version, text = doc.getText();
    if (Buffer.byteLength(text, 'utf8') > 65536) return;
    const current = () => generation === checkGeneration && !doc.isClosed && doc.version === version && vscode.window.activeTextEditor?.document === doc;
    checkTimer = setTimeout(async () => {
      try {
        const result = await runEngine(configuration.get('enginePath'), {text, mode:'fix', deep:false, dictionary:['Parzr']}, current);
        if (!current()) return;
        validatePlan(text, result);
        checked.set(uri, {doc, version, text, result});
        while (checked.size > 32) checked.delete(checked.keys().next().value);
        diagnostics.set(doc.uri, result.edits.map(edit => {
          const range = new vscode.Range(doc.positionAt(edit.start_utf16), doc.positionAt(edit.end_utf16));
          const diagnostic = new vscode.Diagnostic(range, `${edit.explanation || 'Suggested correction'}: ${edit.replacement || 'Remove'}`, vscode.DiagnosticSeverity.Information);
          diagnostic.source = 'Parzr'; diagnostic.code = edit.rule_id; return diagnostic;
        }));
        health.hide();
      } catch (error) {
        if (!current()) return;
        health.text = '$(warning) Parzr'; health.tooltip = error.message; health.show();
      }
    }, 180);
  }
  context.subscriptions.push(diagnostics, health, {dispose:() => {clearTimeout(checkTimer); checkGeneration++; checked.clear();}});
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(event => { if (event.document === vscode.window.activeTextEditor?.document) schedule(); }));
  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(schedule));
  context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(event => { if (event.affectsConfiguration('parzr')) schedule(); }));
  context.subscriptions.push(vscode.workspace.onDidCloseTextDocument(doc => { checked.delete(doc.uri.toString()); diagnostics.delete(doc.uri); }));
  context.subscriptions.push(vscode.languages.registerCodeActionsProvider(proseLanguages.map(language => ({language, scheme:'file'})).concat(proseLanguages.map(language => ({language, scheme:'untitled'}))), {
    provideCodeActions(doc, range) {
      const state = checked.get(doc.uri.toString());
      if (!state || doc.version !== state.version) return [];
      const actions = [];
      for (const edit of state.result.edits) {
        const target = new vscode.Range(doc.positionAt(edit.start_utf16), doc.positionAt(edit.end_utf16));
        if (!range.intersection(target)) continue;
        const action = new vscode.CodeAction(`Change to ${edit.replacement || 'nothing'}`, vscode.CodeActionKind.QuickFix);
        action.command = {command:'parzr.applyInline', title:action.title, arguments:[doc.uri.toString(), state.version, edit.start_utf16]};
        action.isPreferred = true; actions.push(action);
      }
      if (state.result.edits.length) {
        const action = new vscode.CodeAction('Parzr: Fix all grammar', vscode.CodeActionKind.SourceFixAll.append('parzr'));
        action.command = {command:'parzr.applyInline',title:action.title,arguments:[doc.uri.toString(), state.version, null]}; actions.push(action);
      }
      return actions;
    }
  }, {providedCodeActionKinds:[vscode.CodeActionKind.QuickFix,vscode.CodeActionKind.SourceFixAll.append('parzr')]}));
  context.subscriptions.push(vscode.commands.registerCommand('parzr.applyInline', async (uri, version, start) => {
    const state = checked.get(uri);
    if (!state || state.version !== version || state.doc.isClosed || state.doc.version !== version || state.doc.getText() !== state.text || !localDocument(state.doc)) {
      vscode.window.showInformationMessage('Your draft changed. Check the current suggestions.'); return;
    }
    const chosen = start == null ? state.result.edits : state.result.edits.filter(e => e.start_utf16 === start || e.group_id && e.group_id === state.result.edits.find(x => x.start_utf16 === start)?.group_id);
    if (!chosen.length) return;
    const editor = await vscode.window.showTextDocument(state.doc);
    // Focus may have changed while the editor was opening.
    if (state.doc.version !== version || state.doc.getText() !== state.text) return;
    const applied = await editor.edit(builder => { for (const edit of chosen) builder.replace(new vscode.Range(state.doc.positionAt(edit.start_utf16),state.doc.positionAt(edit.end_utf16)),edit.replacement); }, {undoStopBefore:true,undoStopAfter:true});
    if (!applied) vscode.window.showErrorMessage('The editor refused this correction.');
    schedule();
  }));
  schedule();
  context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider('parzr-preview', { provideTextDocumentContent: uri => documents.get(uri.toString()) || '' }));
  context.subscriptions.push(vscode.commands.registerCommand('parzr.rewrite', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.selection.isEmpty) { vscode.window.showInformationMessage('Select the words you want to improve.'); return; }
    if (editor.selections.length !== 1) { vscode.window.showInformationMessage('parzr supports one selection at a time.'); return; }
    const selection = new vscode.Selection(editor.selection.anchor, editor.selection.active);
    const doc = editor.document, version = doc.version, text = doc.getText(selection);
    if (!localDocument(doc)) { vscode.window.showInformationMessage('Parzr uses the engine on this Mac. Open a local prose document.'); return; }
    if (Buffer.byteLength(text, 'utf8') > 65536) { vscode.window.showInformationMessage('Select at most 64 KB of text.'); return; }
    if (!proseLanguages.includes(doc.languageId)) {
      const confirmation = await vscode.window.showWarningMessage('This is a code document. Check only prose or comments; code syntax may produce unwanted suggestions.', 'Check selection as prose');
      if (!confirmation) return;
    }
    const mode = await vscode.window.showQuickPick(modes, { title: 'parzr · Runs on this Mac', placeHolder: 'Choose how to improve your selection' });
    if (!mode) return;
    try {
      const path = vscode.workspace.getConfiguration('parzr').get('enginePath');
      const result = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'Parzr · Checking locally' }, () => runEngine(path, { text, mode: mode.toLowerCase(), deep: true, dictionary: ['Parzr'], sentence_start: /^[\s]*$/.test(doc.lineAt(selection.start.line).text.slice(0, selection.start.character)) || /[.!?]\s*$/.test(doc.lineAt(selection.start.line).text.slice(0, selection.start.character)), sentence_end: doc.offsetAt(selection.end) === doc.getText().length || /[.!?\n]\s*$/.test(text) }));
      validatePlan(text, result);
      if (!result.edits.length) { vscode.window.showInformationMessage('Looks good. No changes needed.'); return; }
      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const original = vscode.Uri.parse(`parzr-preview:/${id}/Original.txt`), rewritten = vscode.Uri.parse(`parzr-preview:/${id}/${mode}.txt`);
      documents.set(original.toString(), text); documents.set(rewritten.toString(), result.text);
      try {
        await vscode.commands.executeCommand('vscode.diff', original, rewritten, `parzr · ${mode} · ${result.edits.length} changes`, { preview: true });
        const action = await vscode.window.showInformationMessage('Review the changes. Your editor keeps its formatting and Undo history.', { modal: true }, 'Apply changes', 'Copy result');
        if (action === 'Copy result') { await vscode.env.clipboard.writeText(result.text); return; }
        if (action !== 'Apply changes') return;
        if (doc.isClosed || doc.version !== version || doc.getText(selection) !== text) throw new Error('Your document changed. Select the text again.');
        const applied = await editor.edit(builder => {
          for (const edit of result.edits) {
            const start = doc.positionAt(doc.offsetAt(selection.start) + edit.start_utf16);
            const end = doc.positionAt(doc.offsetAt(selection.start) + edit.end_utf16);
            builder.replace(new vscode.Range(start, end), edit.replacement);
          }
        }, { undoStopBefore: true, undoStopAfter: true });
        if (!applied) throw new Error('The editor refused these edits. Your document was not changed.');
        await vscode.window.showTextDocument(doc, editor.viewColumn);
      } finally { documents.delete(original.toString()); documents.delete(rewritten.toString()); }
    } catch (error) { vscode.window.showErrorMessage(`parzr: ${error.message}`); }
  }));
}
function validatePlan(text, result) {
  if (!Array.isArray(result.edits) || typeof result.text !== 'string') throw new Error('Invalid edit plan.');
  let end = 0, previousStart = -1;
  for (const edit of result.edits) {
    if (!Number.isInteger(edit.start_utf16) || !Number.isInteger(edit.end_utf16) || edit.start_utf16 < end || edit.start_utf16 === previousStart || edit.end_utf16 < edit.start_utf16 || edit.end_utf16 > text.length || typeof edit.replacement !== 'string' || text.slice(edit.start_utf16, edit.end_utf16) !== edit.original) throw new Error('Invalid edit range.');
    end = edit.end_utf16; previousStart = edit.start_utf16;
  }
  let preview = text;
  for (const edit of [...result.edits].reverse()) preview = preview.slice(0, edit.start_utf16) + edit.replacement + preview.slice(edit.end_utf16);
  if (preview !== result.text) throw new Error('Inconsistent edit plan.');
}
function deactivate() { stopEngine("Parzr closed."); documents.clear(); }
module.exports = { activate, deactivate, validatePlan };
