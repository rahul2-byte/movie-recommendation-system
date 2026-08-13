#!/usr/bin/env bash
# Bootstrap integration test.
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

make_fake_commands() {
  local bin_dir="$1"
  mkdir -p "$bin_dir"

  for command_name in uv node npm; do
    printf '#!/usr/bin/env bash\nexit 0\n' >"$bin_dir/$command_name"
    chmod +x "$bin_dir/$command_name"
  done

  cat >"$bin_dir/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=""
url=""
printf '%s\n' "$*" >>"${FAKE_CURL_ARGS_LOG:?}"
while (($#)); do
  case "$1" in
    -o|--output) output="$2"; shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
printf '%s\n' "$url" >>"$FAKE_CURL_LOG"
if [[ "$url" == *.md5 ]]; then
  printf '0123456789abcdef0123456789abcdef  ml-32m.zip\n' >"$output"
else
  printf 'fixture archive\n' >"$output"
fi
EOF

  cat >"$bin_dir/md5sum" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  [[ "${FAKE_BAD_CHECKSUM:-0}" != "1" ]]
  exit
fi
case "$(basename "$1")" in
  ml-32m.zip)
    if [[ "${FAKE_BAD_CHECKSUM:-0}" == "1" ]]; then
      hash=ffffffffffffffffffffffffffffffff
    else
      hash=0123456789abcdef0123456789abcdef
    fi
    ;;
  links.csv) hash=8f033867bcb4e6be8792b21468b4fa6e ;;
  movies.csv) hash=0df90835c19151f9d819d0822e190797 ;;
  ratings.csv) hash=cf12b74f9ad4b94a011f079e26d4270a ;;
  tags.csv) hash=963bf4fa4de6b8901868fddd3eb54567 ;;
  *) hash=00000000000000000000000000000000 ;;
esac
printf '%s  %s\n' "$hash" "$1"
EOF

  cat >"$bin_dir/unzip" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
destination=""
while (($#)); do
  case "$1" in
    -d) destination="$2"; shift 2 ;;
    *) shift ;;
  esac
done
dataset_dir="$destination/ml-32m"
mkdir -p "$dataset_dir"
printf 'links\n' >"$dataset_dir/links.csv"
printf 'movies\n' >"$dataset_dir/movies.csv"
printf 'ratings\n' >"$dataset_dir/ratings.csv"
if [[ "${FAKE_MISSING_FILE:-0}" != "1" ]]; then
  printf 'tags\n' >"$dataset_dir/tags.csv"
fi
printf 'MovieLens 32M fixture\n' >"$dataset_dir/README.txt"
EOF

  chmod +x "$bin_dir/curl" "$bin_dir/md5sum" "$bin_dir/unzip"
}

make_repo() {
  local name="$1"
  local repo="$TEST_ROOT/$name"
  mkdir -p "$repo/frontend" "$repo/backend/data/raw"
  cp "$SOURCE_ROOT/start.sh" "$repo/start.sh"
  cp "$SOURCE_ROOT/pyproject.toml" "$SOURCE_ROOT/uv.lock" "$repo/"
  cp "$SOURCE_ROOT/frontend/package.json" "$SOURCE_ROOT/frontend/package-lock.json" "$repo/frontend/"
  make_fake_commands "$repo/fake-bin"
  : >"$repo/curl.log"
  : >"$repo/curl-args.log"
  printf '%s\n' "$repo"
}

run_bootstrap() {
  local repo="$1"
  shift
  env \
    PATH="$repo/fake-bin:/usr/bin:/bin" \
    FAKE_CURL_LOG="$repo/curl.log" \
    FAKE_CURL_ARGS_LOG="$repo/curl-args.log" \
    "$@" \
    bash "$repo/start.sh" >/dev/null
}

repo="$(make_repo success)"
run_bootstrap "$repo"
for filename in links.csv movies.csv ratings.csv tags.csv README.txt; do
  [[ -f "$repo/backend/data/raw/$filename" ]] || fail "first run did not install $filename"
done
[[ "$(wc -l <"$repo/curl.log")" -eq 2 ]] || fail "first run did not make exactly two downloads"
rg -q --fixed-strings -- "--progress-bar" "$repo/curl-args.log" || fail "archive download did not show progress"

run_bootstrap "$repo"
[[ "$(wc -l <"$repo/curl.log")" -eq 2 ]] || fail "valid existing data was downloaded again"

repo="$(make_repo checksum-failure)"
printf 'keep\n' >"$repo/backend/data/raw/unrelated.txt"
if run_bootstrap "$repo" FAKE_BAD_CHECKSUM=1; then
  fail "checksum mismatch succeeded"
fi
[[ -f "$repo/backend/data/raw/unrelated.txt" ]] || fail "checksum failure removed unrelated raw data"
[[ ! -f "$repo/backend/data/raw/ratings.csv" ]] || fail "checksum failure installed dataset files"

repo="$(make_repo missing-file)"
if run_bootstrap "$repo" FAKE_MISSING_FILE=1; then
  fail "archive with a missing required file succeeded"
fi
[[ ! -f "$repo/backend/data/raw/ratings.csv" ]] || fail "invalid archive installed partial dataset"

echo "start.sh bootstrap tests passed"
