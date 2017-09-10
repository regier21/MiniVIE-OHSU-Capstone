//looping through args
//command format
/*
node myo_udp --n(optional) numBands --option1 value1 value2 ... --option2 value1 value2 ...

OPTIONS:
--n     Number of armbands.

    Default 1 armband. Takes one value determining number of armbands. If used, must be first option.

--ADD   MAAC address.
    Default for 1 armband can be set above. Value is armband maac address without ':' characters. Can include as many as necessary.

--PORT  Destination port to send to.
    Default is 15001. Include values as necessary in same order as maac address.

--IP    Destination IP.
    Default is localhost. Include values as necessary in same order as maac address.
*/
var MyoBluetooth  = require('MyoNodeBluetoothAPL');
var MyoAgent = new MyoBluetooth();
var argv = require('minimist')(process.argv.slice(2));
console.dir(argv);

var help = 'Streaming Myo Bluetooth in NodeJS.';
var mac = ['f01ccda72c85'];
var port = [15001];
var ip = ['127.0.0.1'];
var numBands = 1;
var debug = 0

// Get help and EXIT
if ( (argv.h) || (argv.help) ) {
    console.log(help);
    process.exit(0);
}

// Get Armband count
if (argv.n === undefined) {
    numBands = 1;
} else {
    numBands = argv.n;
}

console.log('numBands: ' + numBands);

// Get MAC only arg
if (argv._.length) {
    console.log('standAlone arg: ' + argv._);
    mac = argv._;
}


// Get MAC Addresses
mac = argv.MAC
if ( (mac === undefined) || (mac.length < numBands)) {
    console.log('ERROR: Expected ' + numBands + ' MAC Address arguments');
    process.exit(0);
} else {
    console.log('MAC: ' + mac);
}

// Get IP Addresses
ip = argv.IP
if ( (ip === undefined) || (ip.length < numBands)) {
    console.log('ERROR: Expected ' + numBands + ' IP Address arguments');
    process.exit(0);
} else {
    console.log('IP: ' + ip);
}





/*

    else if(process.argv[i] == "--ADD"){ //maac addresses
        for(var j = 1; j <= numBands;j++){
            macAddress[j-1] = process.argv[iArg+j];
        }
   }
    else if(process.argv[i] == "--PORT"){ //ports
        for(var k = 1; k <= numBands;k++){
            port[k-1] = process.argv[iArg+k];
        }
    }
    else if(process.argv[i] == "--IP"){ //ip addresses
        for(var m = 1; m <= numBands;m++){
            ipAdd[m-1] = process.argv[iArg+m];
        }
    }
    else if(process.argv[i] == "--DEBUG"){
        debug = process.argv[iArg+1];
    }
}
*/

process.exit(0)


MyoAgent.setAddress(macAddress);
MyoAgent.setPort(port);
MyoAgent.setIP(ipAdd);
MyoAgent.setDebug(debug);

//Comment this out to remove logging. Logs MAAC addresses, ports, and IP addresses******
console.log("Agent MAC address:" + MyoAgent.MAACaddress);
console.log("Port:" + MyoAgent.port);
console.log("IP Addresses:" + MyoAgent.ipAdd);
if(debug > 0){
    console.log ("Debug Level:" + debug);
}

/*************************************************************/
MyoAgent.on('discovered', function(armband){
    armband.on('connect', function(connected){

        // armband connected succesfully
        if(connected){
            // discover all services/characteristics and enable emg/imu/classifier chars
            this.initStart();
        } else {
            // armband disconnected
        }
    });

    // Armband receives the ready event when all services/characteristics are discovered and emg/imu/classifier mode is enabled
    armband.on('ready', function(){
        // register for events
        armband.on('batteryInfo',function(data){
            if(debug == 2){
                console.log('BatteryInfo: ', data.batteryLevel); //only for critical debug mode
            }
        });

        // read or write data from/to the Myo
        armband.readBatteryInfo();
        armband.setMode();
        armband.on('emg', function(data1){
            //Comment the next line out to remove logging of EMG data
            if(debug == 2){
                console.log("EMG DATA: " + data1.emgData.sample2); //only for critical debug mode
            }
            process.stdout.clearLine();
            process.stdout.cursorTo(0);
        });
    });
    armband.connect();
});
