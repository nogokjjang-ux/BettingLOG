import csv
import io
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, flash, make_response, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///toto_ledger_dev.db").replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1) if os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")) else os.environ.get("DATABASE_URL", "sqlite:///toto_ledger_dev.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

STATUSES = {"pending": "미정산", "won": "적중", "lost": "낙첨", "void": "취소/환불"}

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    sport = db.Column(db.String(40), nullable=False, default="축구")
    league = db.Column(db.String(100), nullable=True, default="")
    event = db.Column(db.String(180), nullable=False)
    market = db.Column(db.String(100), nullable=True, default="")
    odds = db.Column(db.Numeric(10, 3), nullable=False, default=Decimal("1.000"))
    stake = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(12), nullable=False, default="pending", index=True)
    payout = db.Column(db.Integer, nullable=False, default=0)  # actual amount returned, not profit
    note = db.Column(db.String(500), nullable=True, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def net(self):
        return self.payout - self.stake if self.status != "pending" else 0

    @property
    def status_label(self):
        return STATUSES.get(self.status, self.status)


def parse_form(form):
    try:
        bet_date = date.fromisoformat(form.get("bet_date", ""))
        odds = Decimal(form.get("odds", "1"))
        stake = int(form.get("stake", ""))
        payout = int(form.get("payout", "0") or 0)
    except (ValueError, InvalidOperation):
        raise ValueError("날짜, 배당률, 베팅 금액, 환급액을 올바르게 입력해 주세요.")
    status = form.get("status", "pending")
    sport = form.get("sport", "").strip()
    event = form.get("event", "").strip()
    if not sport or not event:
        raise ValueError("종목과 경기명은 필수입니다.")
    if odds <= 0 or stake <= 0 or payout < 0:
        raise ValueError("배당률은 0보다 커야 하며, 베팅 금액은 양수, 환급액은 0 이상이어야 합니다.")
    if status not in STATUSES:
        raise ValueError("정산 상태를 확인해 주세요.")
    if status == "pending":
        payout = 0
    if status == "lost":
        payout = 0
    if status == "void" and payout == 0:
        payout = stake
    return dict(bet_date=bet_date, sport=sport[:40], league=form.get("league", "").strip()[:100], event=event[:180], market=form.get("market", "").strip()[:100], odds=odds, stake=stake, status=status, payout=payout, note=form.get("note", "").strip()[:500])

@app.get("/health")
def health():
    return {"status": "ok"}, 200

@app.get("/")
def index():
    start_raw = request.args.get("start", "").strip()
    end_raw = request.args.get("end", "").strip()
    query = Bet.query
    try:
        start = date.fromisoformat(start_raw) if start_raw else None
        end = date.fromisoformat(end_raw) if end_raw else None
        if start and end and start > end:
            flash("시작일은 종료일보다 늦을 수 없습니다.", "error")
            start = end = None
    except ValueError:
        start = end = None
        flash("기간을 날짜 형식으로 입력해 주세요.", "error")
    if start: query = query.filter(Bet.bet_date >= start)
    if end: query = query.filter(Bet.bet_date <= end)
    bets = query.order_by(Bet.bet_date.desc(), Bet.id.desc()).all()
    total_stake = sum(b.stake for b in bets)
    settled = [b for b in bets if b.status != "pending"]
    settled_stake = sum(b.stake for b in settled)
    payout_total = sum(b.payout for b in settled)
    net = payout_total - settled_stake
    pending_amount = sum(b.stake for b in bets if b.status == "pending")
    roi = (net / settled_stake * 100) if settled_stake else 0
    wins = sum(1 for b in bets if b.status == "won")
    decided = sum(1 for b in bets if b.status in ("won", "lost"))
    win_rate = wins / decided * 100 if decided else 0
    monthly = {}
    for b in bets:
        key = b.bet_date.strftime("%Y-%m")
        monthly.setdefault(key, {"stake": 0, "payout": 0, "net": 0, "pending": 0})
        if b.status == "pending": monthly[key]["pending"] += b.stake
        else:
            monthly[key]["stake"] += b.stake
            monthly[key]["payout"] += b.payout
            monthly[key]["net"] += b.net
    monthly_rows = [{"month": k, **v} for k, v in sorted(monthly.items(), reverse=True)[:12]]
    return render_template("index.html", bets=bets, total_stake=total_stake, payout_total=payout_total, net=net, pending_amount=pending_amount, roi=roi, win_rate=win_rate, wins=wins, decided=decided, monthly_rows=monthly_rows, start=start_raw, end=end_raw, statuses=STATUSES)

@app.route("/bets/new", methods=["GET", "POST"])
def new_bet():
    if request.method == "POST":
        try:
            bet = Bet(**parse_form(request.form))
            db.session.add(bet)
            db.session.commit()
            flash("베팅 기록을 저장했습니다.", "success")
            return redirect(url_for("index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("bet_form.html", bet=None, today=date.today().isoformat(), statuses=STATUSES)

@app.route("/bets/<int:bet_id>/edit", methods=["GET", "POST"])
def edit_bet(bet_id):
    bet = db.get_or_404(Bet, bet_id)
    if request.method == "POST":
        try:
            for key, value in parse_form(request.form).items(): setattr(bet, key, value)
            db.session.commit()
            flash("기록을 수정했습니다.", "success")
            return redirect(url_for("index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("bet_form.html", bet=bet, today=date.today().isoformat(), statuses=STATUSES)

@app.post("/bets/<int:bet_id>/delete")
def delete_bet(bet_id):
    bet = db.get_or_404(Bet, bet_id)
    db.session.delete(bet)
    db.session.commit()
    flash("기록을 삭제했습니다.", "success")
    return redirect(url_for("index"))

@app.get("/export.csv")
def export_csv():
    rows = Bet.query.order_by(Bet.bet_date.desc(), Bet.id.desc()).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ID", "날짜", "종목", "리그", "경기", "베팅 유형", "배당률", "베팅 금액(KRW)", "상태", "실제 환급액(KRW)", "순손익(KRW)", "메모"])
    for b in rows:
        writer.writerow([b.id, b.bet_date.isoformat(), b.sport, b.league, b.event, b.market, str(b.odds), b.stake, b.status_label, b.payout, b.net if b.status != "pending" else "", b.note])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename=toto-ledger-{date.today().isoformat()}.csv"
    return response

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
