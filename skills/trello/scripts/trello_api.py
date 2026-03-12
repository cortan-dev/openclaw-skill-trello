#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

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


class TrelloClient:
    def __init__(self) -> None:
        self.key = os.environ.get("TRELLO_API_KEY")
        self.token = os.environ.get("TRELLO_TOKEN")
        missing = [
            name
            for name, value in {
                "TRELLO_API_KEY": self.key,
                "TRELLO_TOKEN": self.token,
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

    def create_list(self, board_id: str, name: str, pos: str = "bottom") -> Dict[str, Any]:
        return self.request("POST", "/lists", params={"idBoard": board_id, "name": name, "pos": pos})

    def list_cards_on_board(self, board_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/boards/{board_id}/cards", params={"fields": "name,desc,idList,closed,url,dateLastActivity,labels,due,start", "filter": "all"})

    def list_cards_on_list(self, list_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/lists/{list_id}/cards", params={"fields": "name,desc,idList,closed,url,dateLastActivity,labels,due,start", "filter": "all"})

    def get_card(self, card_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/cards/{card_id}", params={"fields": "name,desc,closed,url,dateLastActivity,idBoard,idList,shortLink,labels,due,start", "actions": "commentCard", "actions_limit": 20, "attachments": "true"})

    def create_card(self, list_id: str, name: str, desc: Optional[str] = None, due: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        params = {"idList": list_id, "name": name, "desc": desc, "due": _normalize_date_param(due)}
        if labels:
            params["idLabels"] = ",".join(labels)
        return self.request("POST", "/cards", params=params)

    def move_card(self, card_id: str, list_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"idList": list_id})

    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/actions/comments", params={"text": text})

    def attach_link(self, card_id: str, url: str, name: Optional[str] = None) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/attachments", params={"url": url, "name": name})

    def update_card(self, card_id: str, name: Optional[str] = None, desc: Optional[str] = None, due: Optional[str] = None, start: Optional[str] = None) -> Dict[str, Any]:
        params = {"name": name, "desc": desc, "due": _normalize_date_param(due), "start": _normalize_date_param(start)}
        return self.request("PUT", f"/cards/{card_id}", params=params)

    def set_card_due_date(self, card_id: str, due: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"due": _normalize_date_param(due)})

    def clear_card_due_date(self, card_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"due": "null"})

    def archive_card(self, card_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"closed": "true"})

    def list_board_labels(self, board_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/boards/{board_id}/labels")

    def create_board_label(self, board_id: str, name: str, color: Optional[str] = None) -> Dict[str, Any]:
        return self.request("POST", f"/boards/{board_id}/labels", params={"name": name, "color": color})

    def add_label_to_card(self, card_id: str, label_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/idLabels", params={"value": label_id})

    def remove_label_from_card(self, card_id: str, label_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/cards/{card_id}/idLabels/{label_id}")

    def resolve_label(self, board_id: str, label_ref: str) -> Dict[str, Any]:
        if looks_like_id(label_ref):
            labels = self.list_board_labels(board_id)
            for lb in labels:
                if lb["id"] == label_ref:
                    return lb
            raise NotFoundError(f"No label with ID '{label_ref}' found on this board.")
        labels = self.list_board_labels(board_id)
        matches = [lb for lb in labels if normalize(lb.get("name")) == normalize(label_ref)]
        if not matches:
            raise NotFoundError(f"No label matched '{label_ref}' on this board.")
        if len(matches) > 1:
            raise AmbiguousMatchError("label", label_ref, matches)
        return matches[0]

    def unarchive_card(self, card_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/cards/{card_id}", params={"closed": "false"})

    def archive_list(self, list_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/lists/{list_id}", params={"closed": "true"})

    def unarchive_list(self, list_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/lists/{list_id}", params={"closed": "false"})

    def close_board(self, board_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/boards/{board_id}", params={"closed": "true"})

    def reopen_board(self, board_id: str) -> Dict[str, Any]:
        return self.request("PUT", f"/boards/{board_id}", params={"closed": "false"})

    def list_members_on_board(self, board_id: str) -> List[Dict[str, Any]]:
        return self.request("GET", f"/boards/{board_id}/members", params={"fields": "fullName,username,id"})

    def assign_member_to_card(self, card_id: str, member_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/cards/{card_id}/idMembers", params={"value": member_id})

    def unassign_member_from_card(self, card_id: str, member_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/cards/{card_id}/idMembers/{member_id}")

    def resolve_member(self, member_ref: str, board_id: str) -> Dict[str, Any]:
        if looks_like_id(member_ref):
            data = self.request("GET", f"/members/{member_ref}", params={"fields": "fullName,username,id"})
            return {"id": data["id"], "fullName": data["fullName"], "username": data["username"], "raw": data}

        ref = normalize(member_ref).lstrip("@")
        members = self.list_members_on_board(board_id)
        matches = [m for m in members if normalize(m.get("username")) == ref]
        if not matches:
            matches = [m for m in members if normalize(m.get("fullName")) == normalize(member_ref)]

        if not matches:
            raise NotFoundError(f"No member matched '{member_ref}' on board '{board_id}'.")
        if len(matches) > 1:
            raise AmbiguousMatchError("member", member_ref, matches)

        match = matches[0]
        return {"id": match["id"], "fullName": match["fullName"], "username": match["username"], "raw": match}

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


def _normalize_date_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value.strip().casefold() == "null":
        return "null"
    return value


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
