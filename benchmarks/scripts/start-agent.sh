#!/usr/bin/env bash
# Copyright 2014-2020 Scalyr Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SCRIPT_DIR=$(readlink -f "$(dirname "${BASH_SOURCE[0]}")")

if [[ "${COMMIT_SHA1}" ]]; then
  AGENT_SOURCE_PATH="/agent-source"
  mkdir -p "${AGENT_SOURCE_PATH}"
  echo "Clone agent repository."
  git clone "${AGENT_GIT_URL}" "${AGENT_SOURCE_PATH}"
  cd "${AGENT_SOURCE_PATH}"
  echo "Checkout to target commit."
  git checkout "${COMMIT_SHA1}"
else
  AGENT_SOURCE_PATH=$(realpath "${SCRIPT_DIR}/../..")
fi

cp /config/config.json /config.json

sed -i "s/{API_KEY}/\"${SCALYR_API_KEY}\"/g" /config.json
sed -i "s/{SCALYR_SERVER}/\"${SCALYR_SERVER}\"/g" /config.json
sed -i "s/{SERVER_HOST}/\"${SERVER_HOST}\"/g" /config.json

cat /config.json
mkdir -p ~/scalyr-agent-dev/{log,config,data}
python /agent-source/scalyr_agent/agent_main.py start --no-fork --no-change-user --config=/config.json