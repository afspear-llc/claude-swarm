#!/usr/bin/env bash
# claude-swarm work queue CLI
# Usage: queue.sh <command> [args]
#
# Commands:
#   list [status]                          List tasks, optionally filtered by status
#   add <title> <description> <project> [dispatch] [priority]   Add a task
#   add-team <title> <description> <team-json> [priority]       Add a team task
#   update <id> <field> <value>            Update a single field on a task
#   remove <id>                            Remove a task
#   next-id                                Print the next available ID

set -euo pipefail

QUEUE="${HOME}/.claude/work-queue.json"

# Ensure queue file exists
if [ ! -f "$QUEUE" ]; then
  echo '[]' > "$QUEUE"
fi

cmd="${1:-help}"
shift || true

next_id() {
  local max
  max=$(jq '[.[].id | select(test("^[0-9]+$")) | tonumber] | max // 0' "$QUEUE")
  printf "%03d" $((max + 1))
}

case "$cmd" in

  list)
    status="${1:-}"
    if [ -n "$status" ]; then
      jq --arg s "$status" '[.[] | select(.status == $s)] | .[] | "\(.id)\t\(.status)\t\(.title)"' -r "$QUEUE"
    else
      jq '.[] | "\(.id)\t\(.status)\t\(.title)"' -r "$QUEUE"
    fi
    ;;

  add)
    title="${1:?title required}"
    desc="${2:?description required}"
    project="${3:?project required}"
    dispatch="${4:-auto}"
    priority="${5:-1}"
    id=$(next_id)
    jq --arg id "$id" --arg t "$title" --arg d "$desc" --arg p "$project" \
       --arg disp "$dispatch" --argjson pri "$priority" \
       '. += [{"id":$id,"title":$t,"description":$d,"dispatch":$disp,"project":$p,"status":"ready","priority":$pri}]' \
       "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    echo "✓ Added #${id}: ${title}"
    ;;

  add-team)
    title="${1:?title required}"
    desc="${2:?description required}"
    team_json="${3:?team JSON required}"
    priority="${4:-1}"
    id=$(next_id)
    jq --arg id "$id" --arg t "$title" --arg d "$desc" \
       --argjson team "$team_json" --argjson pri "$priority" \
       '. += [{"id":$id,"title":$t,"description":$d,"dispatch":"team","team":$team,"status":"ready","priority":$pri}]' \
       "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    echo "✓ Added team #${id}: ${title}"
    ;;

  update)
    id="${1:?id required}"
    field="${2:?field required}"
    value="${3:?value required}"
    # Validate field is allowed
    case "$field" in
      status|branch|error|title|description|dispatch|priority|project) ;;
      *) echo "✗ Unknown field: ${field}" >&2; exit 1 ;;
    esac
    # Check task exists
    exists=$(jq --arg id "$id" '[.[] | select(.id == $id)] | length' "$QUEUE")
    if [ "$exists" = "0" ]; then
      echo "✗ Task #${id} not found" >&2
      exit 1
    fi
    # priority is numeric, everything else is string
    if [ "$field" = "priority" ]; then
      jq --arg id "$id" --arg f "$field" --argjson v "$value" \
         'map(if .id == $id then .[$f] = $v else . end)' \
         "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    else
      jq --arg id "$id" --arg f "$field" --arg v "$value" \
         'map(if .id == $id then .[$f] = $v else . end)' \
         "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    fi
    echo "✓ #${id} ${field} → ${value}"
    ;;

  remove)
    id="${1:?id required}"
    exists=$(jq --arg id "$id" '[.[] | select(.id == $id)] | length' "$QUEUE")
    if [ "$exists" = "0" ]; then
      echo "✗ Task #${id} not found" >&2
      exit 1
    fi
    title=$(jq -r --arg id "$id" '.[] | select(.id == $id) | .title' "$QUEUE")
    jq --arg id "$id" 'map(select(.id != $id))' "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    echo "✓ Removed #${id}: ${title}"
    ;;

  next-id)
    next_id
    echo
    ;;

  help|*)
    cat <<'USAGE'
queue.sh <command> [args]

  list [status]                                        List tasks (tab-separated: id, status, title)
  add <title> <description> <project> [dispatch] [pri] Add a single-agent task
  add-team <title> <description> <team-json> [pri]     Add a team task
  update <id> <field> <value>                          Update a field (status, branch, error, etc.)
  remove <id>                                          Remove a task
  next-id                                              Print the next available ID
USAGE
    ;;
esac
