from http.server import BaseHTTPRequestHandler
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.check_card import validate_card_pattern, micro_transaction_check

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
            cards = data.get('cards', [])
            if not cards:
                self.send_response(400); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
                self.wfile.write(json.dumps({"error": "No cards"}).encode()); return
            
            results = []
            for card in cards:
                card_number = str(card.get('card_number', '')).replace(" ", "").replace("-", "")
                exp_month = str(card.get('exp_month', '')); exp_year = str(card.get('exp_year', '')); cvc = str(card.get('cvc', ''))
                masked = card_number[:6] + "******" + card_number[-4:] if len(card_number) >= 10 else "****"
                pattern = validate_card_pattern(card_number)
                if not pattern["valid_pattern"]:
                    results.append({"card_number": masked, "pattern_validation": pattern, "transaction_check": {"transaction_status": "skipped", "decline_reason": "Invalid pattern"}})
                    continue
                transaction = micro_transaction_check(card_number, exp_month, exp_year, cvc)
                results.append({"card_number": masked, "pattern_validation": pattern, "transaction_check": transaction})
            
            valid = sum(1 for r in results if r["transaction_check"]["transaction_status"] == "approved")
            insufficient = sum(1 for r in results if r["transaction_check"].get("decline_code") == "insufficient_funds")
            declined = sum(1 for r in results if r["transaction_check"]["transaction_status"] == "declined" and r["transaction_check"].get("decline_code") != "insufficient_funds")
            skipped = sum(1 for r in results if r["transaction_check"]["transaction_status"] == "skipped")
            
            self.send_response(200); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
            self.wfile.write(json.dumps({"total": len(results), "summary": {"valid_with_funds": valid, "insufficient_balance": insufficient, "declined_other": declined, "invalid_pattern": skipped}, "results": results}).encode())
        except json.JSONDecodeError:
            self.send_response(400); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        except Exception as e:
            self.send_response(500); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS'); self.send_header('Access-Control-Allow-Headers', 'Content-Type'); self.end_headers()
