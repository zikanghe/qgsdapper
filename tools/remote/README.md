# GCP

Main source material:
[github/GCP](https://github.com/GoogleCloudPlatform/deploymentmanager-samples/tree/master/examples/v2/htcondor)
[clould.google.com](https://cloud.google.com/solutions/analyzing-portfolio-risk-using-htcondor-and-compute-engine)
While the tutorial is inspired by the github repo,
one difference between the two is that the tutorial creates custom images,
including an installation of HTCondor.
This is necessary when you're gonna have many nodes,
in which case you won't give them internet access.
So the following follows the tutorial more than the github repo.

## Notable Changes Made

- Tutorial bug was resolved by waiting for internet in startup scripts:

  ```sh
  while ! ping -c1 google.com >/dev/null; do sleep 1 ; done
  ```

- I use `Ubuntu` 2020 Focal Fossa, rather than `Debian-9-stretch,`
  which allows installing htcondor from [Ubuntu's standard software repositories](https://launchpad.net/ubuntu/+source/condor),
  rather than following the installation at [wisc.edu](https://research.cs.wisc.edu/htcondor/debian/)
  which is what the GCP tutorial/github-repo do.
  Thus, my condor is newer (8.6 rather than 8.4),
  which means `condor_submit` and `condor_q` allows option ``-batch-name``.
- Anaconda and DAPPER's requirements have been installed on the compute-node images.
  DAPPER is updated every time experiments are run on GCP,
  but the python libraries in Anaconda are not.
  For example, dill may have been updated on your local computer,
  which could result in the dill version on GCP not knowing how to
  unpack the experiment data you upload to it.
  Dill also requires that the python version (3.8, 3.7, etc) is the same.

## Quotas

Description:
I wish to increase the computing power of my cluster, which is used for HTC in
science. This has been agreed beforehand with my Google Cloud account manager,
eloven@google.com.

Last time around, I just went to the quotas panel,
and selected the quotas that were running close to capacity
(my cluster was already operating at full capacity).
This meant:
+----------------+-------------+-----------------+
|      Name      |    Region   | Requested Limit |
+----------------+-------------+-----------------+
|      CPUS      | us-central1 |      10000      |
| DISKS_TOTAL_GB | us-central1 |      40000      | ie 40 TB
|    NETWORKS    |    GLOBAL   |       100       |
|  SUBNETWORKS   |    GLOBAL   |       996       |
+----------------+-------------+-----------------+

The previous time around I requested:
+----------------+------------------+----------+--------+-------------+
|    Request     | CPUS_ALL_REGIONS | NETWORKS | ROUTES | SUBNETWORKS |
+----------------+------------------+----------+--------+-------------+
| Region: GLOBAL |       1000       |    10    |  500   |     500     |
+----------------+------------------+----------+--------+-------------+
+---------------------+------+
|       Request       | CPUS |
+---------------------+------+
| Region: us-central1 | 1000 |
+---------------------+------+

In general, these are the options I imagine are relevant:
Regions: us-central1-f AND global
CPUs (preemptible?)
Persistent disk standard, SSD, preemptible?
subnetworks
networks
firewall rules


## Reasons why GCP isn't n-nodes x-faster than my workstation

- Its processors (Xenon) are almost 2x slower
- Communication, and loading DAPPER
- Not the case: Truth simulations are not re-run for local runs.
- Not the case: `np` itself uses `mp`.


## ssh to compute-nodes

Even though the compute nodes are configured without internet access,
`gcloud` is still smart enough to ssh into them (using `IAP tunneling`).
This also works despite NORCE firewall,
once it's been configured to allows IP of submit node.
AFAIK, I've done nothing special to enable this. Use for ex:
`gcloud compute ssh condor-compute-pvm-instance-02x5`

## Using standard ssh

This can be enabled with `gcloud compute config-ssh`, which edits a blob in `~/.ssh/config`
Run it "routinely" to update the list.
Another option is to manually look up and use the public IP addresses.

## Opening NORCE firewall for static IP

Reserve static IP:
```bash
the_desc="For submit-node. Known to NORCE firewall to allow outgoing ssh"
name="condor-submit-1"
gcloud compute addresses create $name --project=mc-tut --description="$the_desc" --region=us-central1
```
Consider using IPv6 instead?
List the resulting IP with `gcloud compute addresses list`

Send this IP to Erik Thorsnes for him to open the firewall.
Create the deployment (the cluster). We assume that the submit node is called `condor-submit`

Assign IP. NB:

- change the IP used below

```bash
gcloud compute instances delete-access-config condor-submit --access-config-name="external-nat"
gcloud compute instances add-access-config condor-submit --access-config-name="external-nat" --address=34.72.15.177
gcloud compute instances describe condor-submit
```

## Creating the images
```sh
gcloud compute instances create $MACHINE_NAME \
    --address=34.72.15.177 \
    --zone=us-central1-f --machine-type=n1-standard-1 \
    --image=ubuntu-2004-focal-v20200810 --image-project=ubuntu-os-cloud \
    --boot-disk-size=10GB --metadata-from-file \
    startup-script=~/P/DAPPER/dapper/tools/remote/image-creation/condor-<NODETYPE>.sh
gcloud compute ssh $MACHINE_NAME
# ... Install stuff you want (on top of the essentials of the start-up script)
gcloud compute instances stop --zone=us-central1-f $MACHINE_NAME
gcloud compute images create condor-<NODETYPE>-v<DATE> \
    --source-disk $MACHINE_NAME \
    --source-disk-zone us-central1-f --family htcondor-ubuntu
gcloud compute instances delete $MACHINE_NAME
```

### Updating

When creating the instance from an old image, use
`--image=condor-<NODETYPE>-v<DATE>` and
`--image-project=mc-tut`
You can list the available images with
`gcloud compute images list | rg condor`
Afterward, remember to update the corresponding field in `condor-cluster.yaml`

### Details for condor-submit image

**NB:** The `condor-submit.sh` start-up script must be adapted to OS
```sh
- curl https://bootstrap.pypa.io/get-pip.py | python3 # for Ubuntu
- curl https://bootstrap.pypa.io/get-pip.py | python # for Debian
```
In addition, `autoscaler.py` script must be adapted to python 3 for Ubuntu.
Thereafter, send it with
```sh
gcloud compute scp ~/P/DAPPER/dapper/tools/remote/autoscaler.py pnr@condor-submit:~/
```

**NB**: Immediately (so you don't forget) set-up autoscaler cron job,
**as described in** `autoscaler.py`.
This should also be in effect for other users of htcondor.


### Details for condor-compute image

Follow this recipe
[cloud.google.com](https://cloud.google.com/solutions/analyzing-portfolio-risk-using-htcondor-and-compute-engine#creating_an_htcondor_cluster_by_using_cloud_deployment_manager_templates)
but before stopping the instance and creating the image, do:

- Install dotfiles?

- Install anaconda.
  Install for all users, in `/opt` (as `root`), as described here
  [docs.anaconda.com](https://docs.anaconda.com/anaconda/install/multi-user/),
  i.e.
  - `wget` one of the links from [https://repo.anaconda.com/archive/]
  - Launch installer w/ `sudo bash Anaconda3...sh`
  - Choose to install in `/opt/anaconda`
  - Choose not to initialize Anaconda
  - Create group `sudo groupadd mygroup`
    (use `group add` on Debian)
  - **NB copy-paste one line at a time!**
    It seems the permissions etc. are a bit slow to update!
  - Add group `mygroup` for anaconda:
    ```sh
    sudo chown -R root:mygroup /opt/anaconda
    sudo chmod 770 -R /opt/anaconda
    ```
  - Add `nobody` (username used by htcondor)
    and `pnr` (or whatever username you currently have) to `mygroup`:
    ```sh
    sudo adduser nobody mygroup
    sudo adduser pnr mygroup
    ```
  - Also, put this activation in the `run_job.sh` scripts:
    ```sh
    __conda_setup=$(/opt/anaconda/bin/conda shell.bash hook)
    eval "$__conda_setup"
    conda activate py3.9.6-2021-10-14
    ```
    Ensure the right env name is used to by conda in `run_job.sh`.

- Install DAPPER requirements (while you have internet):
  - Activate conda env.
    NB: make sure the python version agrees with `setup.py:python_requires`.
  - As your ssh login (`pnr`), clone DAPPER,
    `g co dev1`, and do `pip install -e .`
  - Test installation: python `example_1.py`
  - Then `pip uninstall DA-DAPPER` to avoid conflicts with job-time DAPPER installs.

- *Alternatively*, do `pip freeze > reqs.txt` on your local machine, then
  ```sh
  rsync reqs.txt <username>@condor-compute-template.us-central1-f.mc-tut:~/
  ```
  And install (in conda env!) with `pip install -r`.
  If DAPPER was installed in develop mode, simply delete it from `reqs.txt`.
  Also, the specific `matplotlib` version failed to install the last time I tried,
  but I simply installed the latest version instead.

- Redo `chown`ing following the above `pip`ing:
  ```sh
  sudo chown -R root:mygroup /opt/anaconda
  sudo chmod 770 -R /opt/anaconda
  ```
  Ensure this has worked by inspecting:
  ```sh
  ls -l /opt/anaconda/lib/python3.8/site-packages/easy*
  ls -l /opt/anaconda/lib/python3.8/site-packages/tabulate*
  ```


## (Re-)Create deployment/cluster
```sh
gcloud deployment-manager deployments delete htcluster101
gcloud deployment-manager deployments create htcluster101 \
    --config ~/P/DAPPER/dapper/tools/remote/deployment/condor-cluster.yaml
```

You might also have to set the IP to what is opened in NORCE firewall.

One issue that has occurred is that condor-submit didn't get an external IP,
so that ssh didn't work. The IP should be listed doing this:
`gcloud compute instances list`
In that case it sufficed to delete and re- create the deployment.

`gcloud compute ssh condor-submit`
`gcloud compute config-ssh`
Now try normal `ssh`. It might complain that the authenticity
of host `<IP>` can't be established. I believe that's because
of an outdated identification or something
(from previous versions of the cluster) in `~/.ssh/known_hosts`,
which the error message should indicate (with line number).
Just delete this line and try again.

Note: For `uplink.py` to work, you
also need to update to latest `rsync`
and make sure that your `.ssh/config` enables
login without typing passphrase even once.


## Other useful commands
```sh
gcloud compute instances list | wc -l
gcloud compute instance-groups managed list-instances condor-compute-pvm-igm
gcloud compute instance-groups managed describe condor-compute-pvm-igm --zone us-central1-f
gcloud compute instance-groups managed resize condor-compute-pvm-igm --zone=us-central1-f --size 100
condor_rm -all
condor_rm -const 'jobstatus==5'  # rm all jobs on hold (i.e. crashed)
condor_q
condor_q -nobatch -run
condor_q -af ProcId RemoteHost
condor_status -total
condor_tail -f <job-id>
# Logs
grep CRON /var/log/syslog | tail
cat autoscaler.log
du -hs xp # When this is >0, then the job is done
```

## Old stuff

### gsutil

Another way to communicate updated common data to the compute nodes
is to use cloud storage (gsutil).
```python
xcldd=".git|scripts|docs|.*__pycache__.*|.pytest_cache|DA_DAPPER.egg-info|old_version.zip" 
cmd(f"gsutil -m rsync -r -d -x {xcldd} {dirs['DAPPER']} gs://pb2/DAPPER")
```
With this in run_job.sh to pull into compute-nodes:
```sh
mkdir $HOME/DAPPER
CLOUDSDK_PYTHON=/usr/bin/python gsutil -m rsync -d -r gs://pb2/DAPPER DAPPER
```
Drawbacks:

- gsutil requires user to have access to gs bucket.
- gsutil rsync doesnt have --include or --files-from option.


### Dotfiles installation via startup-script
Start-up-script runs as sudo, but need to install for your user.
[inspiration](https://stackoverflow.com/q/43900350)

```sh
sudo useradd -m pnr
sudo -u pnr bash -c 'git clone --bare https://github.com/patricknraanes/dotfiles.git $HOME/.cfg'
_HOME=$(su - pnr -c 'echo $HOME')
cd $_HOME
gitopt="--git-dir=$_HOME/.cfg/ --work-tree=$_HOME"
sudo -u pnr bash -c "git $gitopt config --local status.showUntrackedFiles no"
sudo -u pnr bash -c "git $gitopt checkout --force condor-submit"
sudo -u pnr bash -c "git $gitopt submodule update --init"
```

<!-- markdownlint-configure-file
{
  "blanks-around-fences": false,
  "ul-indent": { "indent": 2 }
}
-->
