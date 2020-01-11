// mplHome.js contains all the javascript for messaging between the mobile app webpage and the MPL Python VIE
// This script file should be used in conjunction with either websocketSpacebrew or websocketNative for low-level messaging
//
// Revisions:
//  28DEC2017 Armiger - Created initial revision and removed prior spacebrew implementation
//  24FEB2018 Armiger - Modularized for either spacebrew or direct websockets
//  27MAR2018 Armiger - Added CSV parsing as basic source of info for classes

// Load the class motion map info as CSV and store as global to generate images and UI buttons
var global_motion_class_data = [];

$(function() {

  jQuery.ajax({
    type: "GET",
    dataType: "text",
    url: "./motion_name_image_map.csv",
    success: function(data) {readCsv(data);}
   });
});


function readCsv(allText) {
  // Parse the CSV and create image gallery

  // Create CSV arrays
  var allTextLines = allText.split(/\r\n|\n/);
  var headerLine = [];

  for (var i=0; i < allTextLines.length; i++) {
      var thisLine = allTextLines[i];

      // Always ignore comment or blank lines
      if (thisLine[0] === "#" || thisLine.length < 1) continue;

      // Split on comma
      var splitLine = thisLine.split(',');

      // populate header
      if (headerLine.length === 0) {
        headerLine = splitLine;
        continue;
      }

      // Populate gallery data for valid entries
      if (splitLine.length === headerLine.length) {
        var className = splitLine[0];
        var classImagePath = splitLine[1];
        global_motion_class_data.push({
            title: className,
            href:  classImagePath,
            type: 'image/' + classImagePath.split('.').pop(),
            thumbnail: classImagePath
          })
      }
  }

  setupGalley();
  setupCallbacks();
}

function routeMessage(cmd_type, cmd_data) {
  // Route the message to the appropriate section of the html page
  // based on the cmd_type.  Pass the target function the cmd_data

  if (cmd_type === "sys_status") {
    $("#msg_status").html(cmd_data);
    $("#msg_status_opt").html(cmd_data);
    $("#msg_status_myo").html(cmd_data);
  }
  if (cmd_type === "training_class") {
    $("#msg_train").text(cmd_data);
  }
  if (cmd_type === "output_class") {
     $("#main_output").text(cmd_data);
     $("#mt_output").text(cmd_data);
     $("#tac_output").text(cmd_data);
  }
  if (cmd_type === "motion_test_status") {
    $("#mt_status").html(cmd_data);
  }
  if (cmd_type === "motion_test_update") {
    updateMTProgressBar(cmd_data);
  }
  if (cmd_type === "motion_test_setup") {
    updateMTImage(cmd_data);
  }
  if (cmd_type === "TAC_status") {
    $("#tac_status").html(cmd_data);
  }
  if (cmd_type === "TAC_setup") {

    // Further parse response (comma separated)
    var tac_setup_data = cmd_data.split(",");

    if (tac_setup_data[0] > 0) {
      $("#tacJoint1Name").text(tac_setup_data[1]);
      updateTACJointTarget(tac_setup_data[2], "tacJoint1Target");
      updateTACJointError(tac_setup_data[3], "tacJoint1Target");
    }
    if (tac_setup_data[0] > 1) {
      $("#tacJoint2Name").text(tac_setup_data[4]);
      updateTACJointTarget(tac_setup_data[5], "tacJoint2Target");
      updateTACJointError(tac_setup_data[6], "tacJoint2Target");
    }
    if (tac_setup_data[0] > 2) {
      $("#tacJoint3Name").text(tac_setup_data[7]);
      updateTACJointTarget(tac_setup_data[8], "tacJoint3Target");
      updateTACJointError(tac_setup_data[9], "tacJoint3Target");
    }
  }

  if (cmd_type === "TAC_update") {
    // Further parse response (comma separated)
    var tac_update_data = cmd_data.split(",");
    if (tac_update_data[0] > 0) {
      updateTACJointBar(tac_update_data[1], "tacJoint1Bar", "tacJoint1Label");
    }
    if (tac_update_data[0] > 1) {
      updateTACJointBar(tac_update_data[2], "tacJoint2Bar", "tacJoint2Label");
    }
    if (tac_update_data[0] > 2) {
      updateTACJointBar(tac_update_data[3], "tacJoint3Bar", "tacJoint3Label");
    }
  }
  if (cmd_type === "strNormalizeMyoPosition") {
	  $("#nmp_status").text(cmd_data);
  }
  if (cmd_type === "strNormalizeMyoPositionImage") {
             updateNMPImage(cmd_data);
  }

  // route joint percept message
  if (cmd_type === "joint_cmd") {
    var cmd_values = cmd_data.split(',');
    $("#SHFE_Cmd").html(cmd_values[0]);
    $("#SHAA_Cmd").html(cmd_values[1]);
    $("#HUM_Cmd").html(cmd_values[2]);
    $("#EL_Cmd").html(cmd_values[3]);
    $("#WRT_Cmd").html(cmd_values[4]);
    $("#WAA_Cmd").html(cmd_values[5]);
    $("#WFE_Cmd").html(cmd_values[6]);
    $("#1AA_Cmd").html(cmd_values[7]);
    $("#1MCP_Cmd").html(cmd_values[8]);
    $("#1PIP_Cmd").html(cmd_values[9]);
    $("#1DIP_Cmd").html(cmd_values[10]);
    $("#2AA_Cmd").html(cmd_values[11]);
    $("#2MCP_Cmd").html(cmd_values[12]);
    $("#2PIP_Cmd").html(cmd_values[13]);
    $("#2DIP_Cmd").html(cmd_values[14]);
    $("#3AA_Cmd").html(cmd_values[15]);
    $("#3MCP_Cmd").html(cmd_values[16]);
    $("#3PIP_Cmd").html(cmd_values[17]);
    $("#3DIP_Cmd").html(cmd_values[18]);
    $("#4AA_Cmd").html(cmd_values[19]);
    $("#4MCP_Cmd").html(cmd_values[20]);
    $("#4PIP_Cmd").html(cmd_values[21]);
    $("#4DIP_Cmd").html(cmd_values[22]);
    $("#5AA_Cmd").html(cmd_values[23]);
    $("#5CMC_Cmd").html(cmd_values[24]);
    $("#5MCP_Cmd").html(cmd_values[25]);
    $("#5DIP_Cmd").html(cmd_values[26]);
  }
  if (cmd_type === "joint_pos") {
    var pos_values = cmd_data.split(',');
    $("#SHFE_Pos").html(pos_values[0]);
    $("#SHAA_Pos").html(pos_values[1]);
    $("#HUM_Pos").html(pos_values[2]);
    $("#EL_Pos").html(pos_values[3]);
    $("#WRT_Pos").html(pos_values[4]);
    $("#WAA_Pos").html(pos_values[5]);
    $("#WFE_Pos").html(pos_values[6]);
    $("#1AA_Pos").html(pos_values[7]);
    $("#1MCP_Pos").html(pos_values[8]);
    $("#1PIP_Pos").html(pos_values[9]);
    $("#1DIP_Pos").html(pos_values[10]);
    $("#2AA_Pos").html(pos_values[11]);
    $("#2MCP_Pos").html(pos_values[12]);
    $("#2PIP_Pos").html(pos_values[13]);
    $("#2DIP_Pos").html(pos_values[14]);
    $("#3AA_Pos").html(pos_values[15]);
    $("#3MCP_Pos").html(pos_values[16]);
    $("#3PIP_Pos").html(pos_values[17]);
    $("#3DIP_Pos").html(pos_values[18]);
    $("#4AA_Pos").html(pos_values[19]);
    $("#4MCP_Pos").html(pos_values[20]);
    $("#4PIP_Pos").html(pos_values[21]);
    $("#4DIP_Pos").html(pos_values[22]);
    $("#5AA_Pos").html(pos_values[23]);
    $("#5CMC_Pos").html(pos_values[24]);
    $("#5MCP_Pos").html(pos_values[25]);
    $("#5DIP_Pos").html(pos_values[26]);
  }
  if (cmd_type === "joint_torque") {
    var torque_values = cmd_data.split(',');
    $("#SHFE_Torque").html(torque_values[0]);
    $("#SHAA_Torque").html(torque_values[1]);
    $("#HUM_Torque").html(torque_values[2]);
    $("#EL_Torque").html(torque_values[3]);
    $("#WRT_Torque").html(torque_values[4]);
    $("#WAA_Torque").html(torque_values[5]);
    $("#WFE_Torque").html(torque_values[6]);
    $("#1AA_Torque").html(torque_values[7]);
    $("#1MCP_Torque").html(torque_values[8]);
    $("#1PIP_Torque").html(torque_values[9]);
    $("#1DIP_Torque").html(torque_values[10]);
    $("#2AA_Torque").html(torque_values[11]);
    $("#2MCP_Torque").html(torque_values[12]);
    $("#2PIP_Torque").html(torque_values[13]);
    $("#2DIP_Torque").html(torque_values[14]);
    $("#3AA_Torque").html(torque_values[15]);
    $("#3MCP_Torque").html(torque_values[16]);
    $("#3PIP_Torque").html(torque_values[17]);
    $("#3DIP_Torque").html(torque_values[18]);
    $("#4AA_Torque").html(torque_values[19]);
    $("#4MCP_Torque").html(torque_values[20]);
    $("#4PIP_Torque").html(torque_values[21]);
    $("#4DIP_Torque").html(torque_values[22]);
    $("#5AA_Torque").html(torque_values[23]);
    $("#5CMC_Torque").html(torque_values[24]);
    $("#5MCP_Torque").html(torque_values[25]);
    $("#5DIP_Torque").html(torque_values[26]);
  }
  if (cmd_type === "joint_temp") {
    var temp_values = cmd_data.split(',');
    $("#SHFE_Temp").html(temp_values[0]);
    $("#SHAA_Temp").html(temp_values[1]);
    $("#HUM_Temp").html(temp_values[2]);
    $("#EL_Temp").html(temp_values[3]);
    $("#WRT_Temp").html(temp_values[4]);
    $("#WAA_Temp").html(temp_values[5]);
    $("#WFE_Temp").html(temp_values[6]);
    $("#1AA_Temp").html(temp_values[7]);
    $("#1MCP_Temp").html(temp_values[8]);
    $("#1PIP_Temp").html(temp_values[9]);
    $("#1DIP_Temp").html(temp_values[10]);
    $("#2AA_Temp").html(temp_values[11]);
    $("#2MCP_Temp").html(temp_values[12]);
    $("#2PIP_Temp").html(temp_values[13]);
    $("#2DIP_Temp").html(temp_values[14]);
    $("#3AA_Temp").html(temp_values[15]);
    $("#3MCP_Temp").html(temp_values[16]);
    $("#3PIP_Temp").html(temp_values[17]);
    $("#3DIP_Temp").html(temp_values[18]);
    $("#4AA_Temp").html(temp_values[19]);
    $("#4MCP_Temp").html(temp_values[20]);
    $("#4PIP_Temp").html(temp_values[21]);
    $("#4DIP_Temp").html(temp_values[22]);
    $("#5AA_Temp").html(temp_values[23]);
    $("#5CMC_Temp").html(temp_values[24]);
    $("#5MCP_Temp").html(temp_values[25]);
    $("#5DIP_Temp").html(temp_values[26]);
  }

}  // routeMessage

function setupCallbacks() {
  // Create callback listeners for commands generated from html

  // Create button click based listeners:
  $("#ID_CLEARCLASS").on("mousedown", function() {sendCmd("Cmd:ClearClass")} );
  $("#ID_CLEARALL").on("mousedown", function() {sendCmd("Cmd:ClearAll")} );
  $("#ID_TRAIN").on("mousedown", function() {sendCmd("Cmd:Train")} );
  $("#ID_SAVE").on("mousedown", function() {sendCmd("Cmd:Save")} );
  $("#ID_BACKUP").on("mousedown", function() {sendCmd("Cmd:Backup")} );
  $("#ID_SPEEDUP").on("mousedown", function() {sendCmd("Cmd:SpeedUp")} );
  $("#ID_SPEEDDOWN").on("mousedown", function() {sendCmd("Cmd:SpeedDown")} );
  $("#ID_HAND_SPEED_UP").on("mousedown", function() {sendCmd("Cmd:HandSpeedUp")} );
  $("#ID_HAND_SPEED_DOWN").on("mousedown", function() {sendCmd("Cmd:HandSpeedDown")} );
  $("#ID_MYO1").on("mousedown", function() {sendCmd("Cmd:RestartMyo1")} );
  $("#ID_MYO2").on("mousedown", function() {sendCmd("Cmd:RestartMyo2")} );
  $("#ID_SELECT_MYO_SET_1").on("mousedown", function() {sendCmd("Cmd:ChangeMyoSet1")} );
  $("#ID_SELECT_MYO_SET_2").on("mousedown", function() {sendCmd("Cmd:ChangeMyoSet2")} );
  $("#ID_RELOAD_ROC").on("mousedown", function() {sendCmd("Cmd:ReloadRoc")} );
  $("#ID_REBOOT").on("mousedown", function() {sendCmd("Cmd:Reboot")} );
  $("#ID_SHUTDOWN").on("mousedown", function() {sendCmd("Cmd:Shutdown")} );
  $("#ID_ASSESSMENT_MT").on("mousedown", function() {startMT()} );
  $("#ID_ASSESSMENT_MT_STOP").on("mousedown", function() {stopMT()} );
  $("#ID_NORMALIZE_MYO_POSITION").on("mousedown", function() {startNMP()} );
  $("#ID_Reset_MYO_POSITION").on("mousedown", function() {sendCmd("Cmd:ResetOrientation")} );
  $("#ID_ASSESSMENT_TAC1").on("mousedown", function() {startTAC1()} );
  $("#ID_ASSESSMENT_TAC3").on("mousedown", function() {startTAC3()} );
  $("#ID_ASSESSMENT_TAC_STOP").on("mousedown", function() {stopTAC()} );
  $("#ID_GOTO_HOME").on("mousedown", function() {sendCmd("Cmd:GotoHome")} );
  $("#ID_GOTO_PARK").on("mousedown", function() {sendCmd("Cmd:GotoPark")} );
  $("#ID_NORMALIZE_UNITY_ORIENTATION").on("mousedown", function() {sendCmd("Cmd:NormUnity")} );
  $("#ID_MYO_SHUTDOWN_1").on("mousedown", function() {sendCmd("Cmd:ShutdownMyo1")} );
  $("#ID_MYO_SHUTDOWN_2").on("mousedown", function() {sendCmd("Cmd:ShutdownMyo2")} );



  // Generate the HTML required to setup buttons for manual control
  var message = []; // append this to create HTML
  var id_list = [];  // Maintain a list of DOM id tags
  var name_list = []; // Maintain a list of classes
  // Add stop bar
  message += '<a href="#" class="ui-btn" id="MAN_Stop1">Stop</a>';

  // Loop through classes and create motion pairs
  var side = 0;
  for (var i_class = 0; i_class < global_motion_class_data.length; i_class++ ){
    var id = 'MAN_' + global_motion_class_data[i_class].title.replace(/ /g,"_"); // changes spaces to underscores
    var name = global_motion_class_data[i_class].title;

    if (name === 'No Movement') {
      continue;
    } else {
      var new_id = 0;
      while (id_list.includes(id)) {
        // generate a new ID
        new_id += 1;
        id = id + new_id.toString();
      }
      id_list.push(id);
      name_list.push(name);
      // console.log(id_list)
    }

    if (global_motion_class_data[i_class].title === 'Hand Open') {
      message += '<a href="#" class="ui-btn" id="'+id+'">'+name+'</a>';
      continue
    }

    if (side === 0) {
      message += '<fieldset class="ui-grid-a">';
      message +=  '<div class="ui-block-a"><a href="#" class="ui-btn" id="' + id + '">' + name + '</a></div>';
      side += 1;
    } else {
      message += '<div class="ui-block-b"><a href="#" class="ui-btn" id="' + id + '">' + name + '</a></div>';
      message += '</fieldset>';
      side = 0;
    }

  }
  // Add stop bar
  message += '<a href="#" class="ui-btn" id="MAN_Stop2">Stop</a>';

  // Now add HTML to the UI page:
  var myElement = document.getElementById("ID_MANUAL_CONTROL");
  var myNewElement = document.createElement("div");
  myNewElement.innerHTML = message;
  myElement.appendChild(myNewElement);

  // Generate Button Callbacks
  for (var i = 0; i < id_list.length; i++ ){
    $("#" + id_list[i]).mousedown("Man:"+name_list[i], function(cmd) {
      sendCmd(cmd.data)
    } );
  }

  // Generate Button Callbacks
  $("#MAN_Stop1").on("mousedown", function() {sendCmd("Man:Stop")} );
  $("#MAN_Stop2").on("mousedown", function() {sendCmd("Man:Stop")} );

  // Create checkbox based switch listeners:
  $('#trainSwitch').on("change", function() { this.checked === true ? sendCmd("Cmd:Add") : sendCmd("Cmd:Stop"); });
  $('#precisionMode').on("change", function() { this.checked === true ? sendCmd("Cmd:PrecisionModeOn") : sendCmd("Cmd:PrecisionModeOff"); });
  $('#pauseAll').on("change", function() { this.checked === true ? sendCmd("Cmd:PauseAllOn") : sendCmd("Cmd:PauseAllOff"); });
  $('#pauseHand').on("change", function() { this.checked === true ? sendCmd("Cmd:PauseHandOn") : sendCmd("Cmd:PauseHandOff"); });
  $('#pauseWristFE').on("change", function() { this.checked === true ? sendCmd("Cmd:PauseWristFEOn") : sendCmd("Cmd:PauseWristFEOff"); });

  // Create slider based switch listeners:
  $('#resetTorque').on("change", function() { this.value === "On" ? sendCmd("Cmd:ResetTorqueOn") : sendCmd("Cmd:ResetTorqueOff"); });
  $('#enableImpedance').on("change", function() { this.value === "On" ? sendCmd("Cmd:ImpedanceOn") : sendCmd("Cmd:ImpedanceOff"); });
  $('#impedanceLevel').on("change", function() { this.value === "Low" ? sendCmd("Cmd:ImpedanceLow") : sendCmd("Cmd:ImpedanceHigh"); });
  $('#autoSave').on("change", function() { this.value === "On" ? sendCmd("Cmd:AutoSaveOn") : sendCmd("Cmd:AutoSaveOff"); });
  $('#autoOpen').on("change", function() { this.value === "On" ? sendCmd("Cmd:AutoOpenOn") : sendCmd("Cmd:AutoOpenOff"); });

  $('#manualControl').on("change", function() { this.value === "On" ? sendCmd("Cmd:ManualControlOn") : sendCmd("Cmd:ManualControlOff"); });
  $('#streamPercepts').on("change", function() { this.value === "On" ? sendCmd("Cmd:JointPerceptsOn") : sendCmd("Cmd:JointPerceptsOff"); });
}  // setupCallbacks

function submitLogMessage() {
  // submitLogMessage called from index.html
  var x = document.getElementById("ID_LOG_MSG").value;
  console.log('Logging ' + x);
  sendCmd("Log:" + x);
}

function startMT() {
  // Gather parameters to send to motion tester
  var repetitions = $("#ID_MT_REPETITIONS").val();
  var timeout = $("#ID_MT_TIMEOUT").val();
  var max_classifications = $("#ID_MT_MAX_CLASSIFICATIONS").val();
  sendCmd("Cmd:StartMotionTester-" + repetitions + "-" + timeout + "-" + max_classifications);
}

function stopMT() {
  sendCmd("Cmd:StopMotionTester");
}

 function startNMP() {
    // Gather parameters to send to myo normalize
    var norm_class = "";
	if(document.getElementById("ID_WEO").checked) {
		norm_class = "Wrist Extend Out"
	}else if(document.getElementById("ID_EF").checked) {
		norm_class = "Elbow Flexion"
	}
    sendCmd("Cmd:StartNormalizeMyo-" + norm_class)
 }

function startTAC1() {
  // Gather parameters to send to TAC1
  var repetitions = $("#ID_REPETITIONS").val();
  var timeout = $("#ID_TIMEOUT").val();
  var dwell_time = $("#ID_DWELL_TIME").val();
  var degree_error = $("#ID_DEGREE_ERROR").val();
  var grasp_error = $("#ID_GRASP_ERROR").val();
  sendCmd("Cmd:StartTAC1-" + repetitions + "-" + timeout + "-" + dwell_time + "-" + degree_error + "-" + grasp_error);
}

function startTAC3() {
  // Gather parameters to send to TAC3
  var repetitions = $("#ID_REPETITIONS").val();
  var timeout = $("#ID_TIMEOUT").val();
  var dwell_time = $("#ID_DWELL_TIME").val();
  var degree_error = $("#ID_DEGREE_ERROR").val();
  var grasp_error = $("#ID_GRASP_ERROR").val();
  sendCmd("Cmd:StartTAC3-" + repetitions + "-" + timeout + "-" + dwell_time + "-" + degree_error + "-" + grasp_error);
}

function stopTAC() {
  sendCmd("Cmd:StopTAC")
}

function updateMTProgressBar(percent) {
  // Function to update the motion tester progress bar based on user input
  // See http://www.w3schools.com/howto/howto_js_progressbar.asp for details
  var elem = document.getElementById("mtProgressBar");
  elem.style.width = percent + '%';
  document.getElementById("mtProgressLabel").innerHTML = percent * 1  + '%';
}

function updateMTImage(imageFile){
  // Function to update motion tester image based on class being assessed
  document.getElementById("ID_MT_IMAGE").src=imageFile
}

// Function to update normalize myo position image based on class being assessed
function updateNMPImage(imageFile){
    document.getElementById("ID_NMP_IMAGE").src=imageFile
}

function updateTACJointBar(value, barId, labelId) {
    var elem = document.getElementById(barId);
    elem.style.marginLeft = value - 2.5 + '%'; // The 2.5 is to account for 5% width
    document.getElementById(labelId).innerHTML = Math.round(value * 1).toString();
}

function updateTACJointError(value, elementId) {
    var elem = document.getElementById(elementId);
    elem.style.width = value*2 + '%'
}

function updateTACJointTarget(value, elementId) {
    var elem = document.getElementById(elementId);
    var percentChar = elem.style.width;
    var percentNum  = percentChar.substring(0, percentChar.length - 1); // Remove percent sign
    var halfWidth = percentNum * 1 / 2;
    var valuePercent = value * 1;
    var newMargin = valuePercent  - halfWidth;
    elem.style.marginLeft = newMargin + '%';
}
