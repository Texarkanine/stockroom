# Project Brief

## User Story

As a maintainer, I want the unpublished semantic default-output change classified as a breaking change before release-please publishes, so the first release that contains the new columns is a major version.

## Use-Case(s)

### Use-Case 1

The default `stockroom semantic` `tsv` and `table` shapes already insert `session_id` and `message_id` before `role` on `main` (`9b1fd45`). That commit is a `feat` and the open release pull request is 1.3.0. Land an empty breaking-change commit on a branch and open a pull request into `main` that the operator can merge. After it is on `main`, release-please can move that release from 1.3.0 to 2.0.0.

## Requirements

1. The branch carries one empty commit: `chore(semantic)!: record the default result-column break`.
2. The commit body has a `BREAKING CHANGE:` footer describing the default `tsv` and `table` column insert (`session_id` and `message_id` before `role`).
3. No product code changes.
4. An open pull request into `main`, ready for the operator to merge, whose title and body carry that same breaking signal so a squash merge still classifies as major.

## Constraints

1. Do not rewrite `9b1fd45`.
2. Do not merge the existing 1.3.0 release pull request.
3. Do not hand-edit that release pull request. release-please regenerates it from commits on `main`.

## Acceptance Criteria

1. The breaking commit is on the branch and is empty of product diff.
2. The pull request into `main` is open and not a draft.
3. The pull request title is the breaking commit subject, and the body includes the `BREAKING CHANGE:` footer.
