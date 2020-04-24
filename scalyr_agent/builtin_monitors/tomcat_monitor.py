# Copyright 2015 Scalyr Inc.
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
# A ScalyrMonitor which monitors the status of the Tomcat application server.
#
# Note, this can be run in standalone mode by:
#     python -m scalyr_agent.run_monitor scalyr_agent.builtin_monitors.tomcat_monitor
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function

import socket
import base64
import re

import six.moves.urllib.parse
import six.moves.http_client
import six.moves.urllib.request
import six.moves.urllib.error
import six.moves.urllib.parse

from scalyr_agent import (
    ScalyrMonitor,
    define_config_option,
    define_metric,
    define_log_field,
)

# needed for BindableHTTPConnection
httpSourceAddress = "127.0.0.1"

__monitor__ = __name__

define_config_option(
    __monitor__,
    "module",
    "Always ``scalyr_agent.builtin_monitors.tomcat_monitor ``",
    required_option=True,
)
define_config_option(
    __monitor__,
    "id",
    "Optional. Included in each log message generated by this monitor, as a field named ``instance``. "
    "Allows you to distinguish between values recorded by different monitors. This is especially "
    "useful if you are running multiple PostgreSQL instances on a single server; you can monitor each "
    "instance with a separate tomcatql_monitor record in the Scalyr Agent configuration.",
    convert_to=six.text_type,
)
define_config_option(
    __monitor__,
    "monitor_url",
    "Name of host machine the agent will connect to PostgreSQL to retrieve monitoring data.",
    convert_to=six.text_type,
    required_option=True,
)
define_config_option(
    __monitor__,
    "monitor_user",
    "The username required to access the monitor URL.",
    convert_to=six.text_type,
)
define_config_option(
    __monitor__,
    "monitor_password",
    "The pasword associated with the monitor_user required to access the monitor URL.",
    convert_to=six.text_type,
)
define_config_option(
    __monitor__,
    "source_address",
    "Optional (defaults to '%s'). The IP address to be used as the source address when fetching "
    "the monitor URL.  Some servers require this to be 127.0.0.1 because they only server the monitor "
    "page to requests from localhost." % httpSourceAddress,
    default=httpSourceAddress,
)

# Metric definitions.
define_metric(
    __monitor__,
    "tomcat.runtime.memory_bytes",
    "The amount of memory free.",
    extra_fields={"type": "free"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.memory_bytes",
    "The total amount of memory available.",
    extra_fields={"type": "total"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.memory_bytes",
    "The maximum amount of memory free.",
    extra_fields={"type": "max"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.threads",
    "The maximum number of threads available/configured.",
    extra_fields={"type": "max"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.threads",
    "The number of threads currently active.",
    extra_fields={"type": "active"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.threads",
    "The number of threads currently busy.",
    extra_fields={"type": "busy"},
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.processing_time_max",
    "The value represents the largest amount of time spent processing a single request.",
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.processing_time",
    "The value represents the largest amount of time spent processing the current request.",
    cumulative=False,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.request_count",
    "The value represents the total number of requests made.",
    cumulative=True,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.error_count",
    "The value represents the total number requests that resulted in errors.",
    cumulative=True,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.network_bytes",
    "The value represents the total number bytes received by the server.",
    extra_fields={"type": "received"},
    cumulative=True,
    category="general",
)
define_metric(
    __monitor__,
    "tomcat.runtime.network_bytes",
    "The value represents the total number sent by the server.",
    extra_fields={"type": "sent"},
    cumulative=True,
    category="general",
)

memory_pools = {
    "cms_old_gen": "The memory pool for objects that have exised for some time in the survivor space / are long lived.",
    "eden_space": "The memory space from which objects are initially allocated.",
    "survivor_space": "The memory pool for objects that have survived garbage collection of the Eden Space.",
    "cms_perm_gen": "Memory used for storing loaded classes.",
    "code_cache": "Memory used for caching the compilation and storage of native code.",
}

for i in memory_pools.keys():
    define_metric(
        __monitor__,
        "tomcat.memory_pools.initial",
        "%s.  The iniital amount of memory allocated to the memory pool."
        % memory_pools[i],
        extra_fields={"pool": i},
        cumulative=False,
        category="memory",
    )
    define_metric(
        __monitor__,
        "tomcat.memory_pools.allocated",
        "%s.  The total amount of memory allocated to the memory pool."
        % memory_pools[i],
        extra_fields={"pool": i},
        cumulative=False,
        category="memory",
    )
    define_metric(
        __monitor__,
        "tomcat.memory_pools.max",
        "%s.  The maximum amount of memory allocated to the memory pool."
        % memory_pools[i],
        extra_fields={"pool": i},
        cumulative=False,
        category="memory",
    )
    define_metric(
        __monitor__,
        "tomcat.memory_pools.used",
        "%s.  The total amount of memory used within the memory pool."
        % memory_pools[i],
        extra_fields={"pool": i},
        cumulative=False,
        category="memory",
    )

define_log_field(__monitor__, "monitor", "Always ``tomcat_monitor``.")
define_log_field(
    __monitor__, "instance", "The ``id`` value from the monitor configuration."
)
define_log_field(
    __monitor__, "metric", 'The name of a metric being measured, e.g. "tomcat.runtime".'
)
define_log_field(__monitor__, "value", "The metric value.")

# Taken from:
#   http://stackoverflow.com/questions/1150332/source-interface-with-python-and-urllib2
#
# For connecting to local machine, specifying the source IP may be required.  So, using
# this mechanism should allow that.  Since getting status requires "opening up" a
# non-standard/user-facing web page, it is best to be cautious.
#
# Note - the use of a global is ugly, but this form is more compatible than with another
# method mentioned which would not require the global.  (The cleaner version was added
# in Python 2.7.)


class BindableHTTPConnection(six.moves.http_client.HTTPConnection):
    def connect(self):
        """Connect to the host and port specified in __init__."""
        self.sock = socket.socket()
        self.sock.bind((self.source_ip, 0))
        if isinstance(self.timeout, float):
            self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))


def BindableHTTPConnectionFactory(source_ip):
    def _get(host, port=None, strict=None, timeout=0):
        # pylint: disable=unexpected-keyword-arg
        if six.PY2:
            kwargs = {"strict": strict}
        else:
            kwargs = {}
        bhc = BindableHTTPConnection(host, port=port, timeout=timeout, **kwargs)
        bhc.source_ip = source_ip
        return bhc

    return _get


class BindableHTTPHandler(six.moves.urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(BindableHTTPConnectionFactory(httpSourceAddress), req)


def _convert_to_megabytes(value):
    # given a value of the form XXXX [MB, KB, GB, TB], convert
    # the value to be represented as megabytes
    parts = value.split(" ")
    if len(parts) < 2:
        return None
    scale_multiplier = {"kb": 0.001, "mb": 1.0, "gb": 1000.0, "tb": 1000000.0}
    if parts[1].lower() not in list(scale_multiplier.keys()):
        return None
    multiplier = scale_multiplier[parts[1].lower()]
    try:
        if "." in parts[0]:
            val = float(parts[0])
        else:
            val = float(int(parts[0]))
    except Exception:
        return None
    return val * multiplier


def _convert_to_milliseconds(value):
    # given a value of the form XXXX [s ms], convert
    # the value to be represented as megabytes
    parts = value.split(" ")
    if len(parts) < 2:
        return None
    scale_multiplier = {
        "s": 1000.0,
        "ms": 1.0,
    }
    if parts[1].lower() not in list(scale_multiplier.keys()):
        return None
    multiplier = scale_multiplier[parts[1].lower()]
    try:
        if "." in parts[0]:
            val = float(parts[0])
        else:
            val = float(int(parts[0]))
    except Exception:
        return None
    return val * multiplier


class TomcatMonitor(ScalyrMonitor):  # pylint: disable=monitor-not-included-for-win32
    """
# Tomcat Monitor

The Tomcat monitor allows you to collect data about the usage and performance of your Tomcat server.

Each monitor can be configured to monitor a specific Tomcat server, thus allowing you to configure alerts and the
dashboard entries independently (if desired) for each instance.

## Configuring TomcatMonitor

In order to use this monitor, you will need to configure a couple of things in your Tomcat
instance:

- Installation of the management utilities
- Adding a user role with monitoring privileges

Installation of the Management Utilities

If you are (or have) installed Tomcat from sources, please consult the documentation for your
version of Tomcat at http://tomcat.apache.org.  For Redhat (and related variants), the
administrator webapps are contained in a package  named tomcat<version>-admin-webapps.
For Debian (and related variants) the administrator webapps are contained in the package
named tomcat<version>-admin.

To check to see, say for Tomcat version 7, if you already have the admin webapps already
installed, you can issue the command 'dpkg -l | grep tomcat7' or look for the file
manager.xml in the directory /etc/tomcat7/Catalina/localhost.

Adding a User Role with Monitoring Privileges

Users are configured in a file named tomcat-users.xml.  This file, for Ubuntu, is located
(for version 7 of Tomcat) in /etc/tomcat7.  Tomcat provides a number of roles with differing
types of access.  For purposes of getting server status, that role is "manager-status".  The
details of the Manager can be found in the Tomcat documentation here:  http://tomcat.apache.org/tomcat-7.0-doc/manager-howto.html

To add user "statusmon" with password "getstatus", you would open up the tomcat-users.xml file
and edit the tomcat-users section to resemble:

<tomcat-users>
  ...
  <role rolename="manager-status"/>
  <user username="statusmon" password="getstatus" roles="manager-status"/>
</tomcat-users>

## Configuring Scalyr Agent

In order to use the Tomcat monitor, you need to enter a configuration in the agent.json
file.  A typical fragment resembles:

  monitors: [
    {
      module:              "scalyr_agent.builtin_monitors.tomcat_monitor",
      id:                  "tomcat",
      monitor_url:         "http://localhost:8080/manager/status",
      monitor_username:    "statusmon",
      monitor_password:    "getstatus"
    }
  ]

Note the ``id`` field in the configurations.  This is an optional field that allows you to specify an identifier
specific to a particular instance of Nginx and will make it easier to filter on metrics specific to that
instance."""

    def _initialize(self):
        """Performs monitor-specific initialization.
        """
        global httpSourceAddress

        # Useful instance variables:
        #   _sample_interval_secs:  The number of seconds between calls to gather_sample.
        #   _config:  The dict containing the configuration for this monitor instance as retrieved from configuration
        #             file.
        #   _logger:  The logger instance to report errors/warnings/etc.

        # determine how we are going to connect
        self._monitor_url = None
        self._monitor_user = None
        self._monitor_password = None
        if "monitor_url" in self._config:
            self._monitor_url = self._config["monitor_url"]
        if "monitor_user" in self._config:
            self._monitor_user = self._config["monitor_user"]
        if "monitor_password" in self._config:
            self._monitor_password = self._config["monitor_password"]
        self._sourceaddress = self._config.get(
            "source_addresss", default=httpSourceAddress
        )
        httpSourceAddress = self._sourceaddress

        if "monitor_url" not in self._config:
            raise Exception("monitor_url must be specified in the configuration.")
        credentials_needed = False
        if "monitor_password" in self._config and "monitor_user" not in self._config:
            credentials_needed = True
        elif "monitor_password" not in self._config and "monitor_user" in self._config:
            credentials_needed = True
        if credentials_needed:
            raise Exception(
                "if monitor_user or monitor_password specified, both must be specified"
            )

    def _get_status(self, url):
        data = None
        # verify that the URL is valid
        try:
            six.moves.urllib.parse.urlparse(url)
        except Exception:
            print(
                "The URL configured for requesting the status page appears to be invalid.  Please verify that the URL is correct in your monitor configuration.  The specified url: %s"
                % url
            )
            return data
        # attempt to request server status
        try:
            request = six.moves.urllib.request.Request(self._monitor_url)
            if self._monitor_user is not None:
                b64cred = base64.encodestring(
                    "%s:%s" % (self._monitor_user, self._monitor_password)
                ).replace("\n", "")
                request.add_header("Authorization", "Basic %s" % b64cred)
            opener = six.moves.urllib.request.build_opener(BindableHTTPHandler)
            handle = opener.open(request)
            data = handle.read()
        except six.moves.urllib.error.HTTPError as err:
            message = (
                "An HTTP error occurred attempting to retrieve the status.  Please consult your server logs to determine the cause.  HTTP error code: %s",
                err.code,
            )
            if err.code == 404:
                message = "The URL used to request the status page appears to be incorrect.  Please verify the correct URL and update your apache_monitor configuration."
            elif err.code == 403:
                message = "The server is denying access to the URL specified for requesting the status page.  Please verify that permissions to access the status page are correctly configured in your server configuration and that your apache_monitor configuration reflects the same configuration requirements."
            elif err.code >= 500 or err.code < 600:
                message = (
                    "The server failed to fulfill the request to get the status page.  Please consult your server logs to determine the cause.  HTTP error code: %s",
                    err.code,
                )
            self._logger.error(message)
            data = None
        except six.moves.urllib.error.URLError as err:
            message = (
                "The was an error attempting to reach the server.  Make sure the server is running and properly configured.  The error reported is: %s"
                % str(err)
            )
            if err.reason.errno == 111:
                message = (
                    "The HTTP server does not appear to running or cannot be reached.  Please check that it is running and is reachable at the address: %s"
                    % url.netloc
                )
            self._logger.error(message)
            data = None
        except Exception as e:
            self._logger.error(
                "An error occurred attempting to request the server status: %s" % e
            )
            data = None
        return data

    def _parse_general_status(self, status):
        # parse general statistics
        # Format is similar to:
        #   Free memory: 6.38 MB Total memory: 16.87 MB Max memory: 123.75 M
        #   Max threads: 200 Current thread count: 1 Current thread busy: 1
        #   Max processing time: 749 ms Processing time: 0.952 s Request count: 42 Error count: 5 Bytes received: 0.00 MB Bytes sent: 0.18 M
        result = {}
        start = status.find("<h1>JVM</h1>")
        if start > -1:
            m = re.match(
                (
                    r"[\w\W]*Free memory: ([\w\W]*) Total memory: ([\w\W]*) Max memory: ([\w\W]*)<\/p>[\w\W]*"
                    r"Max threads: ([\d]*) Current thread count: ([\d]*) Current thread busy: ([\d]*)[\w\W]*"
                    r"Max processing time: ([\w\W]*) Processing time: ([\w\W]*)[\w\W]*"
                    r"Request count: ([\d]*) Error count: ([\d]*) Bytes received: ([\w\W]*) Bytes sent: ([\w\W]*)<\/p><table[\w\W]*"
                ),
                status[start + 12 :],
            )
            if m is not None:
                result["memory_free"] = [
                    "memory_bytes",
                    _convert_to_megabytes(m.group(1)),
                    "type",
                    "free",
                ]
                result["memory_total"] = [
                    "memory_bytes",
                    _convert_to_megabytes(m.group(2)),
                    "type",
                    "total",
                ]
                result["memory_max"] = [
                    "memory_bytes",
                    _convert_to_megabytes(m.group(3)),
                    "type",
                    "max",
                ]
                result["threads_max"] = ["threads", int(m.group(4)), "type", "max"]
                result["threads_current_count"] = [
                    "threads",
                    int(m.group(5)),
                    "type",
                    "active",
                ]
                result["threads_current_busy"] = [
                    "threads",
                    int(m.group(6)),
                    "type",
                    "busy",
                ]
                result["processing_time_max"] = [
                    "processing_time_max",
                    _convert_to_milliseconds(m.group(7)),
                ]
                result["processing_time"] = [
                    "processing_time",
                    _convert_to_milliseconds(m.group(8)),
                ]
                result["request_count"] = ["request_count", int(m.group(9))]
                result["error_count"] = ["error_count", int(m.group(10))]
                result["bytes_received"] = [
                    "network_bytes",
                    _convert_to_megabytes(m.group(11)),
                    "type",
                    "received",
                ]
                result["bytes_sent"] = [
                    "network_bytes",
                    _convert_to_megabytes(m.group(12)),
                    "type",
                    "sent",
                ]
        return result

    def _parse_heap_status(self, status):
        # parse heap statistics
        # TODO -- break this into more granular searches / should be more robust
        result = {}
        start = status.find("<h1>JVM</h1>")
        if start > -1:
            m = re.match(
                (
                    r"[\w\W]*CMS Old Gen<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><\/tr>"
                    r"[\w\W]*Eden Space<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><\/tr>"
                    r"[\w\W]*Survivor Space<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><\/tr>"
                    r"[\w\W]*CMS Perm Gen<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><\/tr>"
                    r"[\w\W]*Code Cache<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><td>([\w\W]*)<\/td><\/tr><\/tbody><\/table>[\w\W]+"
                ),
                status[start + 12 :],
            )
            if m is not None:
                # result["cms_old_gen.type"] = m.group(1)
                result["cms_old_gen.initial"] = [
                    "initial",
                    _convert_to_megabytes(m.group(2)),
                    "pool",
                    "cms_old_gen",
                ]
                result["cms_old_gen.total"] = [
                    "allocated",
                    _convert_to_megabytes(m.group(3)),
                    "pool",
                    "cms_old_gen",
                ]
                result["cms_old_gen.maximum"] = [
                    "max",
                    _convert_to_megabytes(m.group(4)),
                    "pool",
                    "cms_old_gen",
                ]
                result["cms_old_gen.used"] = [
                    "used",
                    _convert_to_megabytes(m.group(5)),
                    "pool",
                    "cms_old_gen",
                ]
                # result["eden_space.type"] = m.group(6)
                result["eden_space.initial"] = [
                    "initial",
                    _convert_to_megabytes(m.group(7)),
                    "pool",
                    "eden_space",
                ]
                result["eden_space.total"] = [
                    "allocated",
                    _convert_to_megabytes(m.group(8)),
                    "pool",
                    "eden_space",
                ]
                result["eden_space.maximum"] = [
                    "max",
                    _convert_to_megabytes(m.group(9)),
                    "pool",
                    "eden_space",
                ]
                result["eden_space.used"] = [
                    "used",
                    _convert_to_megabytes(m.group(10)),
                    "pool",
                    "eden_space",
                ]
                # result["survivor_space.type"] = m.group(11)
                result["survivor_space.initial"] = [
                    "initial",
                    _convert_to_megabytes(m.group(12)),
                    "pool",
                    "survivor_space",
                ]
                result["survivor_space.total"] = [
                    "allocated",
                    _convert_to_megabytes(m.group(13)),
                    "pool",
                    "survivor_space",
                ]
                result["survivor_space.maximum"] = [
                    "max",
                    _convert_to_megabytes(m.group(14)),
                    "pool",
                    "survivor_space",
                ]
                result["survivor_space.used"] = [
                    "used",
                    _convert_to_megabytes(m.group(15)),
                    "pool",
                    "survivor_space",
                ]
                # result["cms_perm_gen.type"] = m.group(16)
                result["cms_perm_gen.initial"] = [
                    "initial",
                    _convert_to_megabytes(m.group(17)),
                    "pool",
                    "cms_perm_gen",
                ]
                result["cms_perm_gen.total"] = [
                    "allocated",
                    _convert_to_megabytes(m.group(18)),
                    "pool",
                    "cms_perm_gen",
                ]
                result["cms_perm_gen.maximum"] = [
                    "max",
                    _convert_to_megabytes(m.group(19)),
                    "pool",
                    "cms_perm_gen",
                ]
                result["cms_perm_gen.used"] = [
                    "used",
                    _convert_to_megabytes(m.group(20)),
                    "pool",
                    "cms_perm_gen",
                ]
                # result["code_cache.type"] = m.group(21)
                result["code_cache.initial"] = [
                    "initial",
                    _convert_to_megabytes(m.group(22)),
                    "pool",
                    "code_cache",
                ]
                result["code_cache.total"] = [
                    "allocated",
                    _convert_to_megabytes(m.group(23)),
                    "pool",
                    "code_cache",
                ]
                result["code_cache.maximum"] = [
                    "max",
                    _convert_to_megabytes(m.group(24)),
                    "pool",
                    "code_cache",
                ]
                result["code_cache.used"] = [
                    "used",
                    _convert_to_megabytes(m.group(25)),
                    "pool",
                    "code_cache",
                ]
        return result

    def gather_sample(self):
        """Invoked once per sample interval to gather a statistic.
        """

        status = self._get_status(self._monitor_url)
        if status is not None:
            status = six.ensure_text(status)
            stats = self._parse_general_status(status)
            heap = self._parse_heap_status(status)

            if stats is not None:
                for key in sorted(stats.keys()):
                    extra = None
                    if len(stats[key]) == 4:
                        extra = {stats[key][2]: stats[key][3]}
                    self._logger.emit_value(
                        "tomcat.runtime.%s" % stats[key][0], stats[key][1], extra
                    )
            if heap is not None:
                for key in sorted(heap.keys()):
                    extra = {heap[key][2]: heap[key][3]}
                    self._logger.emit_value(
                        "tomcat.memory_pools.%s" % heap[key][0], heap[key][1], extra
                    )
