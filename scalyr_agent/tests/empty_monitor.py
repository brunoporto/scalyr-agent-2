# Copyright 2014 Scalyr Inc.
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
# ------------------------------------------------------------------------
#
# author: Imron Alston <imron@scalyr.com>
#
# An empty monitor, that will return immediately without doing anything

from __future__ import unicode_literals
from __future__ import absolute_import

__author__ = "imron@scalyr.com"

import time

from scalyr_agent.scalyr_monitor import ScalyrMonitor


class EmptyMonitor(ScalyrMonitor):  # pylint: disable=monitor-not-included-for-win32
    """
    Monitor class which is running for run_time seconds.
    """

    def run(self, run_time=0.5):
        # We need to eventually call stop otherwise the tests will hang and run forever
        time.sleep(run_time)
        self._run_state.stop()
