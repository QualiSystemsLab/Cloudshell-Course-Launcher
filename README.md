# Cloudshell Course Launcher
This project is an administrative blueprint designed to deploy sandboxes concurrently from a "controller" sandbox. 
Each sandbox is represented in the admin sandbox as a cloudshell service. 
Admin sandbox teardown triggers teardown on all the child sandboxes.

## Installation
- install "Sandbox Controller" Shell as 2G shell
- import Blueprint Packages as 1G Quali Package with "import package" button
- Configure setup scripts to python3 (if server not configured to upload new scripts tot py3 by default)
- Place Launcher blueprint in same domain as courses to be launched
    - course instructor becomes sandbox owner of deployed child sandboxes
    - students added as permitted users
- Add UniversalSettings key to enable web link to child sandbox from servicess 

UniversalSettings Path:
C:\ProgramData\QualiSystems\Settings\Global\ServerUniversalSettings.xml
 ```
 <key name="Sandbox Link" pattern="http://<cloudshell_server>/RM/Diagram/Index/{Sandbox Id}" icon-key="Sandbox Link" />
 ``` 
- replace IP / hostname with Cloudshell server

## Included Blueprint Packages
 1. "Course Launcher"
    - Basic version to deploy sandboxes in parallel
    - health check first sandbox for failed teardown
 2. "Staggered Deploy" 
    - Version with additional inputs to set staggered deployments 
    - useful for vcenter private clouds to distribute deployment load over time
    
NOTE: Both packages utilize the same orchestration scripts, they expose different interface global inputs

## Included Orchestration Scripts
(Included in Blueprint package)
1. Setup script to deploy sandboxes
2. Teardown to clean up sandboxes
3. Extend Sandbox Blueprint Command
   - extend and sync time of all child sandboxes 
   
## Global Inputs on Blueprint
(Included in Blueprint package)
1. Blueprint Course (Required)
    - name of blueprint to be launched
2. Participants List (Required, if "Cloudshell Group" input is blank)
    - comma separated list of valid students
3. Cloudshell Group (Required, if "Participants List" is blank)
    - valid cloudshell group name 
    - can be set as pool of valid options with constraint or left as input string
    - NOTE: Participants List and Cloudshell Groups can both be populated. The users are merged to one list.
4. Deploy Sandboxes Concurrently (Optional)
    - Boolean, EXPECTED constraint ('True', 'False'). 
    - Determines sequential deploy or concurrent.
5. Concurrent Deploy Limit (Optional)
    - Set how many sandboxes can be deployed at one time
    - EXPECTED constraint (None,1,2,3,4,5,6,7,8,9,10)
6. Health Check First (Optional)
    - Boolean, EXPECTED constraint ('True', 'False')
    - If set True the first sandbox deployment will function as health check and setup will stop if this fails.
7. Sandbox Global Inputs (Optional)
    - Global inputs to be forwarded to all children sandboxes. 
    - Input is a semicolon separated key pair chain (key1, val1;key2,val2;key3,val3)
    - no constraints on inputs
