#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This script is used to resize a managed instance group (MIG) cluster

based on the number of jobs in the HTCondor queue.

The script comes from a Google Cloud Platform (GCP) tutorial,
but has been slightly modified since. Notably, we use python3,
and a different version of HTCondor.
Also see notes on "ClasaAd" in DAPPER's `_get_job_status`.

NB: When my user changed (from `pnr` to `para`) I no longer had access to
`googleapiclient`, `oauth2client`, installed at the bottom of
the startup script for condor-submit. Fixed by doing
```sh
/usr/bin/python3 -m pip install oauth2client
/usr/bin/python3 -m pip install google-api-python-client
```

Install script using
```sh
gcloud compute scp ~/P/DAPPER/dapper/tools/remote/autoscaler.py condor-submit:~/
gcloud compute ssh condor-submit
chmod u+x autoscaler.py
crontab -e
```
and then add
```cron
*/2 * * * *  /usr/bin/python3 $HOME/autoscaler.py -p mc-tut -z us-central1-f -g condor-compute-pvm-igm -v 1 >> $HOME/autoscaler.log 2>&1
```
"""

# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pprint import pprint
try:
    from googleapiclient import discovery  # type: ignore
    from oauth2client.client import GoogleCredentials  # type: ignore
except ImportError:
    print("Could not import Google tools.")
    from sys import exit; exit()

import os
import math
import argparse


####################
#  Args, defaults  #
####################

parser = argparse.ArgumentParser("autoscaler.py")
parser.add_argument("-p" , "--project_id"           , help="Project id"                                                                   , type=str)
parser.add_argument("-r" , "--region"               , help="GCP region where the managed instance group is located"                       , type=str)
parser.add_argument("-z" , "--zone"                 , help="Name of GCP zone where the managed instance group is located"                 , type=str)
parser.add_argument("-g" , "--group_manager"        , help="Name of the managed instance group"                                           , type=str)
parser.add_argument("-c" , "--computeinstancelimit" , help="Maximum number of compute instances"                                          , type=int)
parser.add_argument("-v" , "--verbosity"            , help="Increase output verbosity. 1-show basic debug info. 2-show detail debug info" , type=int  , choices=[0 , 1 , 2])
args = parser.parse_args()

# Project ID
project = args.project_id  # Ex:'slurm-var-demo'

# Region where the managed instance group is located
region = args.region  # Ex: 'us-central1'

# Name of the zone where the managed instance group is located
zone = args.zone  # Ex: 'us-central1-f'

# The name of the managed instance group.
instance_group_manager = args.group_manager  # Ex: 'condor-compute-igm'

# Default number of running instances that the managed instance group should maintain at any given time.
# This number will go up and down based on the load (number of jobs in the queue)
size = 0

# Debug level: 1-print debug information, 2 - print detail debug information
debug = 0
if (args.verbosity):
    debug = args.verbosity

# Timestamp to enable probing if script is being run as cron job.
print('\n================================')
from datetime import datetime
import pytz
now = datetime.now(pytz.timezone('Europe/Oslo'))
timestamp = now.strftime("%Y / %m / %d - %H:%M:%S (%Z)")
print(timestamp)


# Limit for the maximum number of compute instance.
# If zero (default), will be set to MIG's maxSurge.
compute_instance_limit = 0
if (args.computeinstancelimit):
    compute_instance_limit = abs(args.computeinstancelimit)



if debug > 0:
    print('autoscaler.py launched with the following arguments:')
    print('    project_id:'           , project)
    print('    region:'               , region)
    print('    zone:'                 , zone)
    print('    group_manager:'        , instance_group_manager)
    print('    computeinstancelimit:' , compute_instance_limit)
    print('    debuglevel:'           , debug)



############################
#  Misc API functionality  #
############################

# Obtain credentials
credentials = GoogleCredentials.get_application_default()
service = discovery.build('compute', 'v1', credentials=credentials)

# Remove specified instance from MIG and decrease MIG size
def deleteFromMig(instances):
    base_url = ('https://www.googleapis.com/compute/v1'
                + '/projects/' + project
                + '/zones/' + zone
                + '/instances/')
    instances_to_delete = {'instances': [base_url + x for x in instances]}

    requestDelInstance = service.instanceGroupManagers().deleteInstances(
        project=project,
        zone=zone, instanceGroupManager=instance_group_manager,
        body=instances_to_delete)
    response = requestDelInstance.execute()
    if debug > 1:
        print('Request to delete instance ', instances)
        pprint(response)

    return response


def getInstanceTemplateInfo():
    requestTemplateName = \
        service.instanceGroupManagers().get(project=project, zone=zone,
            instanceGroupManager=instance_group_manager,
            fields='instanceTemplate')
    responseTemplateName = requestTemplateName.execute()
    template_name = ''

    if debug > 1:
        print('Request for the template name')
        pprint(responseTemplateName)

    if len(responseTemplateName) > 0:
        template_url = responseTemplateName.get('instanceTemplate')
        template_url_partitioned = template_url.split('/')
        template_name = \
            template_url_partitioned[len(template_url_partitioned) - 1]

    requestInstanceTemplate = \
        service.instanceTemplates().get(project=project,
            instanceTemplate=template_name, fields='properties')
    responseInstanceTemplateInfo = requestInstanceTemplate.execute()

    if debug > 1:
        print('Template information')
        pprint(responseInstanceTemplateInfo['properties'])

    machine_type = responseInstanceTemplateInfo['properties']['machineType']
    is_preemtible = responseInstanceTemplateInfo['properties']['scheduling']['preemptible']
    request = service.machineTypes().get(project=project, zone=zone,
            machineType=machine_type)
    response = request.execute()
    guest_cpus = response['guestCpus']
    if debug > 1:
        print('Machine information')
        pprint(responseInstanceTemplateInfo['properties'])

    instanceTemlateInfo = {'machine_type': machine_type,
                           'is_preemtible': is_preemtible,
                           'guest_cpus': guest_cpus}
    print()
    return instanceTemlateInfo


def get_node_status():
    """Find nodes that are not busy (all slots showing status as "Unclaimed")."""
    # Get slot status (via Condor)
    slot_names = os.popen('condor_status -af name state').read().splitlines()
    if debug > 1:
        print('Current status of compute slots reported by Condor')
        print(slot_names)
    # Combine slots status into node status
    node_busy = {}
    for slot_name in slot_names:
        # hostname, status
        try:
            host, status = slot_name.split()
        except ValueError:
            continue
        # Slot, node
        try:
            slot, node = host.split('@')
        except ValueError:
            slot = "NO-SLOT"
            node = host
        node = node.split('.')[0]
        # Print
        if debug > 1:
            print(", ".join([slot, node, status]))

        slot_is_busy = status != "Unclaimed"
        if node not in node_busy:
            node_busy[node] = slot_is_busy
        else:
            node_busy[node] |= slot_is_busy

    # As a safety measure, use another method to set node_busy to True
    # NB: I tried parsing this
    # job_hosts = os.popen('condor_q -nobatch -run').read().splitlines()
    # but sometimes only partial lines were returned. So instead use this:
    job_hosts = os.popen('condor_q -af ProcId RemoteHost').read().splitlines()
    if debug > 1:
        print('Current job hosts')
        print(job_hosts)
    for line in job_hosts:
        try:
            job_id, host = line.split()
            slot, node = host.split('@')
            node = node.split(".")[0]
        except ValueError:
            continue
        else:
            if node in node_busy:
                node_busy[node] = True
            else:
                # Condor will eventually re-assign the node, but this takes a long time.
                print("Warning: Job", job_id, "should run on node", node)
                print("but this node appears to have been shut down.")

    if debug > 1:
        print('Compute node busy status:')
        print(node_busy)

    return node_busy


##############
#  MIG info  #
##############
instanceTemlateInfo = getInstanceTemplateInfo()
if debug > 0:
    print('Information about the compute instance template')
    pprint(instanceTemlateInfo)

cores_per_node = instanceTemlateInfo['guest_cpus']
print('Number of CPU per compute node:', cores_per_node)

requestGroupInfo = service.instanceGroupManagers().get(project=project,
        zone=zone, instanceGroupManager=instance_group_manager)
responseGroupInfo = requestGroupInfo.execute()

MIG_maxSurge = responseGroupInfo["updatePolicy"]["maxSurge"]["calculated"]
if compute_instance_limit == 0:
    compute_instance_limit = MIG_maxSurge

currentTarget = int(responseGroupInfo['targetSize'])
print('\nCurrent MIG target size:', currentTarget)

if debug > 1:
    print('MIG Information:')
    print(responseGroupInfo)


##############
#  Job info  #
##############
# in the queue that includes number of jos waiting as well as number of jobs already assigned to nodes
# queue_length_req = 'condor_q -totals -format "%d " Jobs -format "%d " Idle -format "%d " Held'
queue_length_req = 'condor_q -totals'
queue_length_resp = os.popen(queue_length_req).read().split()
# Parse output
if len(queue_length_resp) > 1:
    inds = {k[:-1]: queue_length_resp.index(k)-1 for k in ["jobs;","idle,","held,"]}

    queue        = int(queue_length_resp[inds["jobs"]])
    idle_jobs    = int(queue_length_resp[inds["idle"]])
    on_hold_jobs = int(queue_length_resp[inds["held"]])
else:
    queue        = 0
    idle_jobs    = 0
    on_hold_jobs = 0

print("Queue")
print("    Length:", queue)
print("    Waiting:", idle_jobs)
print("    On hold:", on_hold_jobs)

# Adjust current queue length by the number of jos that are on-hold
queue -= on_hold_jobs
print("Adjusted queue length:", queue)


################################
#  Calculate ideal (MIG size)  #
################################

# Calculate number of VM instances for current job queue length
if queue > 0:
    size = float(queue) / float(cores_per_node)
    size = int(math.ceil(size))

    if debug > 0:
        print("=> Max. required MIG size (num. of instances): %d/%d = %d"
              %(queue, cores_per_node, size))

    # Here it's tempting to re-adjust size by dividing by `jobs_per_core` or smth.
    # However, that would produce Zeno's paradox (tortoise vs Achilles).
    # => Better to rely on the `compute_instance_limit` setting.

    # Limit/bound instance numbers
    if size > compute_instance_limit:
        size = compute_instance_limit
        print("But MIG size is limited at", compute_instance_limit)

else:
    size = 0

print('=> New MIG target size:', size)


#################
#  Adjustments  #
#################
if size == 0 and currentTarget == 0:
    print('No jobs in the queue and no compute instances running. Nothing to do')
    exit()

if size == currentTarget:
    print('Running correct number of compute nodes')
    exit()

if size < currentTarget:
    print('Scaling down. Looking for nodes that are not busy and so can be shut down' )
    idle = [node for node, busy in get_node_status().items() if not busy]
    print("\n    ".join(["Shutting down these VMs:"] + idle))
    respDel = deleteFromMig(idle)
    if debug > 1:
        print("Scaling down complete")

if size > currentTarget:
    print("Scaling up. Need to increase number of instances to", size)
    #Request to resize
    request = service.instanceGroupManagers().resize(project=project,
            zone=zone,
            instanceGroupManager=instance_group_manager,
            size=size)
    response = request.execute()
    if debug > 1:
        print('Requesting to increase MIG size')
        pprint(response)
        print("Scaling up complete")
