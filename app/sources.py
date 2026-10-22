"""Netzabrufe: eine Stelle für alle Quellen (QuestStoreDB, Steam, gg.deals).

Übernommen aus dem eShopKompass: ehrliche Kennung, nur öffentliche Ziele, Grenzen für
Antwortgröße und Zeit. Alle Abrufe laufen über `fetch(url)`, damit Tests eine Attrappe
einsetzen können.
"""
import http.cookiejar
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
import zlib

VERSION = "0.5.2"

# Das Tool gibt sich immer als es selbst zu erkennen. Antwortet eine Quelle mit
# einer Sperre (403, 429) oder einer Prüfseite, hört es auf, statt sich zu tarnen.
USER_AGENT = f"vr-navigator/{VERSION} (privates Sammlungs-Tool)"
BLOCKED = (403, 429)


def blocked_target(url):
    """Grund, warum das Tool eine Adresse nicht abruft, sonst "". Abgerufen wird nur das
    öffentliche Internet: Eigene Links könnten sonst Geräte im Heimnetz oder
    den Server selbst ansprechen. Geprüft wird jede Adresse, die der Name ergibt; lässt er sich
    hier nicht auflösen (etwa hinter einem Proxy), entscheidet der Abruf selbst."""
    p = urllib.parse.urlsplit(str(url or ""))
    if p.scheme not in ("http", "https"):
        return "nur http und https"
    if p.username or p.password:
        return "Adresse mit Zugangsdaten"
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
        infos = socket.getaddrinfo(p.hostname or "", port, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError, UnicodeError):
        return ""
    for info in infos:
        try:
            ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        except ValueError:
            continue
        if not ip.is_global:
            return "Adresse nicht öffentlich"
    return ""


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Weiterleitungen nur ins öffentliche Internet."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        why = blocked_target(newurl)
        if why:
            raise urllib.error.URLError(f"Weiterleitung abgelehnt: {why}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), _SafeRedirect)


class FetchError(Exception):
    def __init__(self, url, status, detail=""):
        super().__init__(f"{status} bei {url} {detail}".strip())
        self.url, self.status = url, status


MAX_BODY = 20 << 20      # größte Antwort, gepackt und entpackt: Shopseiten haben unter 2 MB


def _inflate(raw, wbits):
    d = zlib.decompressobj(wbits)
    out = d.decompress(raw, MAX_BODY + 1)
    if len(out) > MAX_BODY:
        raise ValueError("Antwort zu groß")
    return out


def _decode(raw, enc):
    if enc == "gzip":
        return _inflate(raw, 16 + zlib.MAX_WBITS)
    if enc == "deflate":
        try:
            return _inflate(raw, zlib.MAX_WBITS)
        except zlib.error:
            return _inflate(raw, -zlib.MAX_WBITS)
    return raw


def request(url, ua=None, timeout=25, encoding="gzip, deflate", headers=None):
    """HTTP GET ohne Ausnahme: liefert Status, Text und Kopfdaten für die Diagnose."""
    headers = {
        "User-Agent": ua or USER_AGENT,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "Accept-Encoding": encoding,
        **(headers or {}),
    }
    req = urllib.request.Request(url, headers=headers)
    out = {"url": url, "status": 0, "text": "", "enc": "", "server": "", "error": ""}
    out["error"] = blocked_target(url)
    if out["error"]:
        return out
    try:
        try:
            resp = _opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            resp = e                      # Fehlerseiten haben auch einen Inhalt
        with resp:
            raw = resp.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise ValueError("Antwort zu groß")
            out["status"] = getattr(resp, "status", None) or resp.getcode()
            out["enc"] = (resp.headers.get("Content-Encoding") or "").lower()
            out["server"] = resp.headers.get("Server") or ""
            if out["enc"] not in ("", "identity", "gzip", "deflate") and encoding != "identity":
                return request(url, ua, timeout, "identity", headers)   # z. B. Brotli
            charset = resp.headers.get_content_charset() or "utf-8"
            out["text"] = _decode(raw, out["enc"]).decode(charset, errors="replace")
    except Exception as e:                # Zeitüberschreitung, DNS, TLS
        out["error"] = str(e)[:160]
    return out


def fetch(url, timeout=25, ua=None, headers=None):
    """HTTP GET, gibt Text zurück. Wirft FetchError mit Statuscode."""
    r = request(url, ua, timeout, headers=headers)
    if r["error"]:
        raise FetchError(url, 0, r["error"])
    if r["status"] >= 400:
        raise FetchError(url, r["status"])
    return r["text"]


def challenge(text):
    """Prüfseite statt Inhalt (Cloudflare „Just a moment…“), sonst "". Das Hintergrundskript
    „challenge-platform“ allein genügt nicht: Es steht auch in normalen Seiten."""
    t = str(text or "")[:200_000]
    if "cf_chl_opt" in t or "<title>Just a moment" in t:
        return "Prüfseite von Cloudflare"
    return ""
