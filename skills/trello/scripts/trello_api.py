#!/usr/bin/env python3
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
    def __init__(self, kind: str, query: str, matches: List[Dict[str, Any]]):
        self.kind = kind
        self.query = query
        self.matches = matches
        names = ", ".join(f"{m.get('name', '<unnamed>')} ({m.get('id')})" for m in matches)
        super().__init__(f"Multiple {kind}s matched '{query}': {names}. Clarify with a unique exact name or Trello id.")


class NotFoundError(TrelloError):
    pass


class TrelloClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("TRELLO_API_KEY")
        self.token = os.environ.get("TRELLO_TOKEN")
        if not self.api_key or not self.token:
            raise TrelloError("Missing Trello credentials. Set TRELLO_API_KEY and TRELLO_TOKEN.")

    def _request(self, method: str, path: str, query: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
        params = {"key": self.api_key, "token": self.token}
        if query:
            params.update({k: v for k, v in query.items() if v is not None})
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params, doseq=True)}"
        body = None
        headers = {"Accept": "application/json"}
        if data is not None:
            payload = urllib.parse.urlencode({k: v for k, v in data.items() if v is not None})
            body = payload.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TrelloError(f"Trello API {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise TrelloError(f"Network error calling Trello API: {exc}") from exc

    def get(self, path: str, query: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, query=query)

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None) -> Any:
        merged = dict(data or {})
        if query:
            merged.update(query)
        return self._request("POST", path, data=merged)

    def put(self, path: str, data: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None) -> Any:
        merged = dict(data or {})
        if query:
            merged.update(query)
        return self._request("PUT", path, data=merged)

    def get_boards(self) -> List[Dict[str, Any]]:
        return self.get("/members/me/boards", {"fields": "name,desc,url,closed,dateLastActivity"})

    def create_board(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        return self.post("/boards", {"name": name, "desc": description})

    def get_board(self, board_id: str) -> Dict[str, Any]:
        return self.get(f"/boards/{board_id}", {"fields": "name,desc,url,closed,dateLastActivity", "lists": "open"})

    def get_lists(self, board_id: str) -> List[Dict[str, Any]]:
        return self.get(f"/boards/{board_id}/lists", {"fields": "name,closed,pos"})

    def create_list(self, board_id: str, name: str, pos: str = "bottom") -> Dict[str, Any]:
        return self.post("/lists", {"name": name, "idBoard": board_id, "pos": pos})

    def get_cards_for_board(self, board_id: str) -> List[Dict[str, Any]]:
        return self.get(f"/boards/{board_id}/cards", {"fields": "name,desc,idList,closed,url,shortUrl"})

    def get_cards_for_list(self, list_id: str) -> List[Dict[str, Any]]:
        return self.get(f"/lists/{list_id}/cards", {"fields": "name,desc,idList,closed,url,shortUrl"})

    def create_card(self, list_id: str, name: str, desc: Optional[str] = None) -> Dict[str, Any]:
        return self.post("/cards", {"idList": list_id, "name": name, "desc": desc})

    def get_card(self, card_id: str) -> Dict[str, Any]:
        return self.get(f"/cards/{card_id}", {"actions": "commentCard", "actions_limit": 20, "attachments": "true"})

    def update_card(self, card_id: str, *, name: Optional[str] = None, desc: Optional[str] = None, id_list: Optional[str] = None, closed: Optional[bool] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if desc is not None:
            payload["desc"] = desc
        if id_list is not None:
            payload["idList"] = id_list
        if closed is not None:
            payload["closed"] = "true" if closed else "false"
        return self.put(f"/cards/{card_id}", payload)

    def add_comment(self, card_id: str, text: str) -> Dict[str, Any]:
        return self.post(f"/cards/{card_id}/actions/comments", {"text": text})

    def attach_link(self, card_id: str, url: str, name: Optional[str] = None) -> Dict[str, Any]:
        return self.post(f"/cards/{card_id}/attachments", {"url": url, "name": name})

    def resolve_board(self, board_ref: str) -> Dict[str, Any]:
        boards = self.get_boards()
        return resolve_by_name_or_id("board", board_ref, boards)

    def resolve_list(self, board_id: str, list_ref: str) -> Dict[str, Any]:
        lists = self.get_lists(board_id)
        return resolve_by_name_or_id("list", list_ref, lists)

    def resolve_card(self, *, board_id: Optional[str] = None, list_id: Optional[str] = None, card_ref: str) -> Dict[str, Any]:
        if list_id:
            cards = self.get_cards_for_list(list_id)
        elif board_id:
            cards = self.get_cards_for_board(board_id)
        else:
            raise TrelloError("resolve_card requires board_id or list_id")
        return resolve_by_name_or_id("card", card_ref, cards)


def resolve_by_name_or_id(kind: str, query: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    exact_id = [item for item in items if item.get("id") == query]
    if len(exact_id) == 1:
        return exact_id[0]
    exact_name = [item for item in items if item.get("name") == query]
    if len(exact_name) == 1:
        return exact_name[0]
    if len(exact_name) > 1:
        raise AmbiguousMatchError(kind, query, exact_name)
    lowered = query.lower()
    ci_name = [item for item in items if str(item.get("name", "")).lower() == lowered]
    if len(ci_name) == 1:
        return ci_name[0]
    if len(ci_name) > 1:
        raise AmbiguousMatchError(kind, query, ci_name)
    contains = [item for item in items if lowered in str(item.get("name", "")).lower()]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        raise AmbiguousMatchError(kind, query, contains)
    raise NotFoundError(f"No {kind} matched '{query}'.")


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def fail(exc: Exception) -> None:
    print(str(exc), file=sys.stderr)
    sys.exit(1)
