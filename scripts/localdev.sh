#!/bin/sh
#
# Contributor localdev helpers: skills mirror, clean, and status.
# Invoked by the root Makefile; do not call from end-user install paths.
#
# Usage:
#   localdev.sh skills --harness cursor|claude [--repo-root DIR]
#   localdev.sh clean  --harness cursor|claude [--repo-root DIR]
#   localdev.sh status [--repo-root DIR] [--shim-dest PATH]
#
set -eu

MARKER_BEGIN="# BEGIN stockroom-local (managed by 'make localdev')"
MARKER_END="# END stockroom-local"
CURSOR_SKILLS_REL=".cursor/skills/stockroom-local"
PRE_COMMIT_REL=".git/hooks/pre-commit"
DEFAULT_SHIM_DEST="${HOME}/.local/bin/stockroom"

# Resolve a file path to a canonical form without GNU readlink -f.
#
# Globals:
#   None
# Arguments:
#   $1 - Path to a file (not necessarily existing as a regular file)
# Outputs:
#   Canonical path on STDOUT
# Returns:
#   0 always
canon_file() {
	cf_target="${1}"
	cf_dir=$(dirname -- "${cf_target}")
	cf_base=$(basename -- "${cf_target}")
	if [ -d "${cf_dir}" ]; then
		printf '%s/%s\n' "$(CDPATH='' cd -P -- "${cf_dir}" && pwd)" "${cf_base}"
	else
		printf '%s\n' "${cf_target}"
	fi
}

# Strip a managed BEGIN/END block from a file (idempotent).
#
# Globals:
#   MARKER_BEGIN, MARKER_END
# Arguments:
#   $1 - Path to the file
# Outputs:
#   None
# Returns:
#   0 on success; 1 if awk/mv fails
strip_managed_block() {
	smb_file="${1}"
	smb_tmp="${smb_file}.tmp"
	awk -v b="${MARKER_BEGIN}" -v e="${MARKER_END}" \
		'$0 == b { skip = 1 }
		!skip { print }
		$0 == e { skip = 0 }' \
		"${smb_file}" > "${smb_tmp}"
	mv "${smb_tmp}" "${smb_file}"
}

# Ensure a shebang on the pre-commit hook, then (re)append the managed block.
#
# Globals:
#   MARKER_BEGIN, MARKER_END
# Arguments:
#   $1 - Path to .git/hooks/pre-commit
#   $2 - Relative skills-mirror path to guard (from repo root)
# Outputs:
#   None
# Returns:
#   0 on success
install_pre_commit_guard() {
	ipcg_hook="${1}"
	ipcg_skills_rel="${2}"
	ipcg_tmp="${ipcg_hook}.tmp"

	touch "${ipcg_hook}"
	if ! head -n 1 "${ipcg_hook}" 2>/dev/null | grep -q '^#!'; then
		{ printf '#!/bin/sh\n'; cat "${ipcg_hook}"; } > "${ipcg_tmp}"
		mv "${ipcg_tmp}" "${ipcg_hook}"
	fi

	strip_managed_block "${ipcg_hook}"

	{
		printf '%s\n' "${MARKER_BEGIN}"
		printf '%s\n' \
			"if git diff --cached --name-only -- ${ipcg_skills_rel} | grep -q .; then git reset --quiet HEAD -- ${ipcg_skills_rel}; fi"
		printf '%s\n' "${MARKER_END}"
	} >> "${ipcg_hook}"
	chmod +x "${ipcg_hook}"
}

# Mirror skills/* into the Cursor localdev skills farm.
#
# Globals:
#   None
# Arguments:
#   $1 - Absolute repo root
# Outputs:
#   Status lines to STDOUT
# Returns:
#   0 on success
skills_cursor() {
	sc_root="${1}"
	sc_dir="${sc_root}/${CURSOR_SKILLS_REL}"
	sc_hook="${sc_root}/${PRE_COMMIT_REL}"

	mkdir -p "${sc_dir}"
	for sc_link in "${sc_dir}"/*; do
		[ -L "${sc_link}" ] || continue
		sc_name=$(basename -- "${sc_link}")
		[ -d "${sc_root}/skills/${sc_name}" ] || rm -f "${sc_link}"
	done
	for sc_skill in "${sc_root}"/skills/*/; do
		[ -d "${sc_skill}" ] || continue
		sc_name=$(basename -- "${sc_skill}")
		ln -sfn "../../../skills/${sc_name}" "${sc_dir}/${sc_name}"
	done

	install_pre_commit_guard "${sc_hook}" "${CURSOR_SKILLS_REL}"
	echo "local-skills (cursor): mirrored skills into ${CURSOR_SKILLS_REL}"
}

# Claude has no nested skills farm; session load uses --plugin-dir.
#
# Globals:
#   None
# Arguments:
#   $1 - Absolute repo root
# Outputs:
#   Reminder to STDOUT
# Returns:
#   0 always
skills_claude() {
	sc_root="${1}"
	echo "local-skills (claude): no skills mirror; use \`claude --plugin-dir ${sc_root}\` for a session-scoped plugin load"
}

# Remove Cursor localdev-managed artifacts (skills mirror + pre-commit).
#
# Globals:
#   MARKER_BEGIN, MARKER_END
# Arguments:
#   $1 - Absolute repo root
# Outputs:
#   Status lines to STDOUT
# Returns:
#   0 on success
clean_cursor() {
	cc_root="${1}"
	cc_dir="${cc_root}/${CURSOR_SKILLS_REL}"
	cc_hook="${cc_root}/${PRE_COMMIT_REL}"

	if [ -d "${cc_dir}" ]; then
		for cc_link in "${cc_dir}"/*; do
			[ -e "${cc_link}" ] || [ -L "${cc_link}" ] || continue
			[ -L "${cc_link}" ] && rm -f "${cc_link}"
		done
		rmdir "${cc_dir}" 2>/dev/null || true
	fi

	if [ -f "${cc_hook}" ]; then
		strip_managed_block "${cc_hook}"
		chmod +x "${cc_hook}"
	fi
	echo "localdev-clean (cursor): removed skills mirror and pre-commit block (idempotent)"
}

# Claude has no on-disk skills farm to remove.
#
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   Status line to STDOUT
# Returns:
#   0 always
clean_claude() {
	echo "localdev-clean (claude): no skills mirror to remove"
}

# Remove the on-path shim only when it is a localdev (owner=dev) claim.
#
# Leaves harness-owned shims (cursor/claude) untouched. Dest absent is a no-op.
# After removal, stockroom is off PATH until a normal install binds it again
# (rectify never creates a missing shim).
#
# Globals:
#   None
# Arguments:
#   $1 - Shim destination path (usually ~/.local/bin/stockroom)
# Outputs:
#   Status lines to STDOUT
# Returns:
#   0 always (refusal to delete non-dev is not an error)
unclaim_dev_shim() {
	uds_dest="${1}"
	uds_owner=""

	if [ ! -f "${uds_dest}" ]; then
		echo "localdev-clean: shim absent (${uds_dest})"
		return 0
	fi

	uds_owner=$(awk '/^# STOCKROOM_OWNER=/ { sub(/^# STOCKROOM_OWNER=/, ""); print; exit }' "${uds_dest}")
	if [ "${uds_owner}" != "dev" ]; then
		echo "localdev-clean: leaving shim in place (owner='${uds_owner:-unknown}', not 'dev')"
		return 0
	fi

	rm -f "${uds_dest}"
	echo "localdev-clean: removed localdev shim (${uds_dest}, owner=dev)"
	echo "localdev-clean: stockroom is off PATH until you reinstall the marketplace plugin and run sr-initialize (shim install)"
}

# Print localdev-managed + shim status (read-only).
#
# Globals:
#   MARKER_BEGIN, DEFAULT_SHIM_DEST
# Arguments:
#   $1 - Absolute repo root
#   $2 - Shim destination path
# Outputs:
#   Status report to STDOUT
# Returns:
#   0 always (facts are never errors)
print_status() {
	ps_root="${1}"
	ps_dest="${2}"
	ps_skills="${ps_root}/${CURSOR_SKILLS_REL}"
	ps_hook="${ps_root}/${PRE_COMMIT_REL}"
	ps_path_shim=""
	ps_owner=""
	ps_app_dir=""
	ps_gen=""
	ps_py=""
	ps_torch=""
	ps_path_canon=""
	ps_dest_canon=""

	echo "=== localdev-managed ==="
	if [ -d "${ps_skills}" ] && ls -A "${ps_skills}" >/dev/null 2>&1; then
		echo "  skills-mirror: PRESENT (${CURSOR_SKILLS_REL})"
		# Intentional: operator-facing listing of the skills farm (names + symlink targets).
		# shellcheck disable=SC2012
		ls -la "${ps_skills}" | sed 's/^/    /'
	else
		echo "  skills-mirror: absent (${CURSOR_SKILLS_REL})"
	fi
	if [ -f "${ps_hook}" ] && grep -qF "${MARKER_BEGIN}" "${ps_hook}" 2>/dev/null; then
		echo "  pre-commit managed block: PRESENT"
	else
		echo "  pre-commit managed block: absent"
	fi

	echo ""
	echo "=== shim ==="
	ps_path_shim=$(command -v stockroom 2>/dev/null || true)
	if [ -n "${ps_path_shim}" ]; then
		echo "  on-PATH: ${ps_path_shim}"
	else
		echo "  on-PATH: absent (stockroom not on PATH)"
	fi

	if [ ! -f "${ps_dest}" ]; then
		echo "  dest: absent (${ps_dest})"
		return 0
	fi

	echo "  dest: ${ps_dest}"
	ps_owner=$(awk '/^# STOCKROOM_OWNER=/ { sub(/^# STOCKROOM_OWNER=/, ""); print; exit }' "${ps_dest}")
	ps_app_dir=$(awk '/^# STOCKROOM_APP_DIR=/ { sub(/^# STOCKROOM_APP_DIR=/, ""); print; exit }' "${ps_dest}")
	ps_gen=$(awk '/^# STOCKROOM_GENERATOR_VERSION=/ { sub(/^# STOCKROOM_GENERATOR_VERSION=/, ""); print; exit }' "${ps_dest}")

	if [ -z "${ps_owner}" ] || [ -z "${ps_app_dir}" ]; then
		echo "  header: unreadable / not a stockroom shim"
		return 0
	fi

	echo "  owner: ${ps_owner}"
	echo "  app-dir: ${ps_app_dir}"
	if [ -n "${ps_gen}" ]; then
		echo "  generator: ${ps_gen}"
	fi
	if [ -f "${ps_app_dir}/pyproject.toml" ]; then
		echo "  app-dir alive: yes"
	else
		echo "  app-dir alive: no (missing pyproject.toml)"
	fi

	ps_py="${ps_app_dir}/.venv/bin/python"
	if [ -x "${ps_py}" ]; then
		ps_torch=$("${ps_py}" -c 'import torch; print(torch.__version__)' 2>/dev/null) \
			|| ps_torch="not installed"
		echo "  torch (engine venv): ${ps_torch}"
	else
		echo "  torch (engine venv): no .venv python at ${ps_py}"
	fi

	if [ -n "${ps_path_shim}" ]; then
		ps_path_canon=$(canon_file "${ps_path_shim}")
		ps_dest_canon=$(canon_file "${ps_dest}")
		if [ "${ps_path_canon}" != "${ps_dest_canon}" ]; then
			echo "  warning: on-PATH stockroom is not ${ps_dest}"
		fi
	fi
}

usage() {
	cat <<'EOF' >&2
Usage:
  localdev.sh skills --harness cursor|claude [--repo-root DIR]
  localdev.sh clean  --harness cursor|claude [--repo-root DIR]
  localdev.sh status [--repo-root DIR] [--shim-dest PATH]
EOF
}

# Parse argv and dispatch.
#
# Globals:
#   DEFAULT_SHIM_DEST
# Arguments:
#   Full script argv
# Outputs:
#   Subcommand output / usage on error
# Returns:
#   0 on success; 1 on usage/validation error
main() {
	m_cmd=""
	m_harness=""
	m_repo_root=""
	m_shim_dest="${DEFAULT_SHIM_DEST}"
	m_script_dir=""

	if [ "$#" -lt 1 ]; then
		usage
		return 1
	fi

	m_cmd="${1}"
	shift

	while [ "$#" -gt 0 ]; do
		case "${1}" in
			--harness)
				[ "$#" -ge 2 ] || { usage; return 1; }
				m_harness="${2}"
				shift 2
				;;
			--repo-root)
				[ "$#" -ge 2 ] || { usage; return 1; }
				m_repo_root="${2}"
				shift 2
				;;
			--shim-dest)
				[ "$#" -ge 2 ] || { usage; return 1; }
				m_shim_dest="${2}"
				shift 2
				;;
			-h|--help)
				usage
				return 0
				;;
			*)
				echo "localdev.sh: unknown argument: ${1}" >&2
				usage
				return 1
				;;
		esac
	done

	m_script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
	if [ -z "${m_repo_root}" ]; then
		m_repo_root=$(CDPATH='' cd -- "${m_script_dir}/.." && pwd)
	else
		m_repo_root=$(CDPATH='' cd -- "${m_repo_root}" && pwd)
	fi

	case "${m_cmd}" in
		skills|clean)
			case "${m_harness}" in
				cursor|claude) ;;
				*)
					echo "localdev.sh: --harness must be 'cursor' or 'claude' (got: '${m_harness}')" >&2
					return 1
					;;
			esac
			;;
		status) ;;
		*)
			echo "localdev.sh: unknown command: ${m_cmd}" >&2
			usage
			return 1
			;;
	esac

	case "${m_cmd}" in
		skills)
			if [ "${m_harness}" = "claude" ]; then
				skills_claude "${m_repo_root}"
			else
				skills_cursor "${m_repo_root}"
			fi
			;;
		clean)
			if [ "${m_harness}" = "claude" ]; then
				clean_claude
			else
				clean_cursor "${m_repo_root}"
			fi
			unclaim_dev_shim "${m_shim_dest}"
			;;
		status)
			print_status "${m_repo_root}" "${m_shim_dest}"
			;;
	esac
}

main "$@"
