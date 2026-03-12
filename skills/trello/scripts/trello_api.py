#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

BASE_URL = "https://api.trello.com/1"


class TrelloError(Exception):
    pass


class AmbiguousMatchError(TrelloError):
    def __init__(self, entity_type: str, query: str, matches: List[Dict[str, Any]]):
        self.entity_type = entity_type
        self.query = query
        self.matches = matches
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        options = []
        for item in self.matches[:10]:
            context_bits = []
            if item.get("board_name"):
                context_bits.append(f"board={item['board_name']}")
            if item.get("list_name"):
                context_bits.append(f"list={item['list_name']}")
            context = f" ({', '.join(context_bits)})" if context_bits else ""
            options.append(f"- {item.get('name', '<unnamed>')} [{item.get('id', '?')}]" + context)
        joined = "\n".join(options)
        return (
            f"Multiple {self.entity_type}s matched '{self.query}'. Ask exactly one clarifying question and have the user choose one of these options:\n{joined}"
        )


class NotFoundError(TrelloError):
    pass


@dataclass
class ResolutionContext:
    board_name: Optional[str] = None
    list_name: Optional[str] = None


class TrelloClient:
    def __init__(self) -> None:
        self.key = os.environ.get("TRELLO_API_KEY")
        self.token = os.environ.get("TRELLO_TOKEN")
        self.secret = os.environ.get("TRELLO_API_SECRET")
        missing = [
            name
            for name, value in {
                "TRELLO_API_KEY": self.key,
                "TRELLO_TOKEN": self.token,
                "TRELLO_API_SECRET": self.secret,
            }.items()
            if not value
        ]
        if missing:
            raise TrelloError(f"Missing Trello env vars: {', '.join(missing)}")

    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Any:
        query = {"key": self.key, "token": self.token}
        if params:
            query.update({k: v for k, v in params.items() if v is not None})
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query, doseq=True)}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TrelloError(f"Trello API {exc.code} for {method.upper()} {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise TrelloError(f"Network error calling Trello API: {exc}") from exc

    def create_board(self, name: str, desc: Optional[str] = None) -> Dict[str, Any]:
        return self.request("POST", "/boards", params={"name": name, "desc": desc, "defaultLists": "false"})

    def list_boards(self) -> List[Dict[str, Any]]:
        return self.request("GET", "/members/me/boards", params={"fields": "name,desc,closed,url,dateLastActivity"})

    def get_board(self, board_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/boards/{board_id}", params={"fields": "name,desc,closed,url,dateLastActivity,idOrganization,prefs"})

    def list_lists(self, board_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/boards/{board_id}/lists", params={"fields": "name,closed,pos", "filter": "all"})

    def create_list(self, board_id: str, name: str) -> Dict[str, Any]:
        return self.request("POST", "/lists", params={"idBoard": board_id, "name": name})

    def list_cards_on_board(self, board_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/boards/{board_id}/cards", params={"fields": "name,desc,idList,closed,url,dateLastActivity", "filter": "all"})

    def list_cards_on_list(self, list_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/lists/{list_id}/cards", params={"fields": "name,desc,idList,closed,url,dateLastActivity", "filter": "all"})

    def get_card(self, card_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/cards/{card_id}", params={"fields": "name,desc,closed,url,dateLastActivity,idBoard,idList,shortLink", "actions": "commentCard", "actions_limit": 20, "attachments": "true"})

    def create_card(self, list_id: str, name: str, desc: Optional[str] = None) -> Dict[str, Any]:
        return self.request("POST", "/cards", params={"idList": list_id, "name": name, "desc": desc})

    def move_card(self, card_id: str, list_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"idList": list_id})

    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/actions/comments", params={"text": text})

    def attach_link(self, card_id: str, url: str, name: Optional[str] = None) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/attachments", params={"url": url, "name": name})

    def update_card(self, card_id: str, name: Optional[str] = None, desc: Optional[str] = None) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"name": name, "desc": desc})

    def archive_card(self, card_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"closed": "true"})

    def resolve_board(self, board: str) -> Dict[str, Any]:
        if looks_like_id(board):
            data = self.get_board(board)
            return {"id": data["id"], "name": data["name"], "raw": data}
        boards = self.list_boards()
        matches = [b for b in boards if normalize(b.get("name")) == normalize(board)]
        if not matches:
            raise NotFoundError(f"No board matched '{board}'.")
        if len(matches) > 1:
            raise AmbiguousMatchError("board", board, matches)
        match = matches[0]
        return {"id": match["id"], "name": match["name"], "raw": match}

    def resolve_list(self, list_ref: str, board_ref: Optional[str] = None) -> Dict[str, Any]:
        if looks_like_id(list_ref):
            data = self.request("GET", f"/lists/{list_ref}", params={"fields": "name,closed,idBoard,pos"})
            board = self.get_board(data["idBoard"])
            return {"id": data["id"], "name": data["name"], "board_id": data["idBoard"], "board_name": board["name"], "raw": data}
        if not board_ref:
            raise TrelloError("List name resolution requires --board unless you provide a Trello list ID.")
        board = self.resolve_board(board_ref)
        lists = self.list_lists(board["id"])
        matches = []
        for lst in lists:
            if normalize(lst.get("name")) == normalize(list_ref):
                item = dict(lst)
                item["board_name"] = board["name"]
                matches.append(item)
        if not matches:
            raise NotFoundError(f"No list matched '{list_ref}' on board '{board['name']}'.")
        if len(matches) > 1:
            raise AmbiguousMatchError("list", list_ref, matches)
        match = matches[0]
        return {"id": match["id"], "name": match["name"], "board_id": board["id"], "board_name": board["name"], "raw": match}

    def resolve_card(self, card_ref: str, board_ref: Optional[str] = None, list_ref: Optional[str] = None) -> Dict[str, Any]:
        if looks_like_id(card_ref):
            data = self.get_card(card_ref)
            board = self.get_board(data["idBoard"])
            lst = self.request("GET", f"/lists/{data['idList']}", params={"fields": "name"})
            return {
                "id": data["id"],
                "name": data["name"],
                "board_id": data["idBoard"],
                "board_name": board["name"],
                "list_id": data["idList"],
                "list_name": lst["name"],
                "raw": data,
            }
        if list_ref:
            lst = self.resolve_list(list_ref, board_ref)
            cards = self.list_cards_on_list(lst["id"])
            matches = []
            for card in cards:
                if normalize(card.get("name")) == normalize(card_ref):
                    item = dict(card)
                    item["board_name"] = lst["board_name"]
                    item["list_name"] = lst["name"]
                    matches.append(item)
        elif board_ref:
            board = self.resolve_board(board_ref)
            lists_by_id = {lst["id"]: lst for lst in self.list_lists(board["id"])}
            cards = self.list_cards_on_board(board["id"])
            matches = []
            for card in cards:
                if normalize(card.get("name")) == normalize(card_ref):
                    item = dict(card)
                    item["board_name"] = board["name"]
                    item["list_name"] = lists_by_id.get(card.get("idList"), {}).get("name")
                    matches.append(item)
        else:
            raise TrelloError("Card name resolution requires --board or --list unless you provide a Trello card ID.")
        if not matches:
            raise NotFoundError(f"No card matched '{card_ref}'.")
        if len(matches) > 1:
            raise AmbiguousMatchError("card", card_ref, matches)
        match = matches[0]
        return {
            "id": match["id"],
            "name": match["name"],
            "board_name": match.get("board_name"),
            "list_name": match.get("list_name"),
            "list_id": match.get("idList"),
            "raw": match,
        }


def normalize(value: Optional[str]) -> str:
    return (value or "").strip().casefold()


def looks_like_id(value: str) -> bool:
    text = (value or "").strip()
    return len(text) == 24 and all(ch in "0123456789abcdefABCDEF" for ch in text)


def parse_json_arg(raw: Optional[str]) -> Optional[Any]:
    if raw is None:
        return None
    return json.loads(raw)


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main_guard(fn):
    try:
        fn()
    except TrelloError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
