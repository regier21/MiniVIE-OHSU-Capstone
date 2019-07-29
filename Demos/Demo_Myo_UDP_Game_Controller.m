% Sample Myo UDP controller for games
% By David Samson
% July 1, 2016

% Send controller data via UDP based on Myo input
% Contains simplified and complex control schemes
% To use simplified, simply cancel selection of training data
% To use complex, when prompted, select appropriate training data

a = PnetClass(3452,5005,'192.168.56.101');
a.initialize;

joystickType = 'Default'; % SNES equivalent. May use 2 axes and up to 8 buttons
a.putData([255 uint8('T') uint8(joystickType)]) %send joystick selection to reciever


% Create arrays to hold the buttons and the control axes
btns = [0 0 0 0 0 0 0 0];
axes = [0 0];


% Determine type of control scheme by Myo band
simpleControl = true; % Myo controls using raw emg magnitudes 
% Try to load training data file
hData = PatternRecognition.TrainingData();
if (hData.loadTrainingData())
    simpleControl = false; % Myo controls using LDA classifier
end


% Create EMG Myo Interface Object
hMyo = Inputs.MyoUdp.getInstance();
hMyo.initialize();
 
% Create LDA Classifier Object
hLda = SignalAnalysis.Lda;
hLda.initialize(hData);
hLda.train();
hLda.computeError();
classes = hLda.getClassNames;

% Store the 6 most recent states of the predicted hand motion.
% Current motion is determined by the mode of these states
% Start with no movement (9)
state = [9 9 9 9 9 9];



% Array specifying which Myo channels to use for simple control model
mChannels = [4,7];

% Amount to scale the difference of the emg signals by
% higher increases joystick range, but decreases control precision
mScale = 100000; 

% Store 10 most recent simple control states to smooth simple control output
avgABS = zeros(1,10);
%%

% May want to tweak which classes cause what button presses/axis movement
StartStopForm([]); 
while StartStopForm 
    
    btns = [0 0 0 0]; %reset buttons after each loop
    %axes = [0 0]; %hold axes from previous loop
    
    % Get the appropriate number of EMG samples for the 8 myo channels
    emgData = hMyo.getData(hLda.NumSamplesPerWindow,1:8);
    
    
    if (simpleControl)
        % Do simple control model
        % To use, wear Myo band with logo facing outward, and notification
        % LED pointing downward on forearm. Only control input provided in
        % this mode is simple left and right joystick input. No buttons.
        avgABS(2:end) = avgABS(1:end-1);
        avgABS(1) = diff(abs(emgData(1,mChannels)))*mScale;
        axes(1) = int16(mean(avgABS))
    else
        % Complex control model
        % Generate button presses and joystick positions for current data
        % classification of Myo emg signals according to LDA classifier
        % Extract features and classify
        features2D = hLda.extractfeatures(emgData);
        [classDecision, voteDecision] = hLda.classify(reshape(features2D',[],1));



        % Push current class decision into state buffer
        state(2:end) = state(1:end-1);
        state(1) = classDecision;
        state;
        classDecision = mode(state);


        % Perform controller states based on class decision mode
        % setup for left/right input and one button for jumping
        switch(char(classes(classDecision)))
            case 'Wrist Rotate In'
                fprintf('wrist rotate in\n');
                axes(1) = 32767; %joystick X = right
            case 'Wrist Rotate Out'
                fprintf('wrist rotate out\n');
                axes(1) = -32767; %joystick X = left
            case 'Wrist Flex In'
                fprintf('wrist flex in\n');
                axes(1) = 32767;  %joystick X = right
            case 'Wrist Extend Out'
                fprintf('wrist extend out\n');
                axes(1) = -32767;  %joystick X = left
            case 'Cylindrical Grasp'
                fprintf('cylindrical grasp\n');
                btns(1) = 1;   %press jump button
            case 'Tip Grasp'
                fprintf('tip grasp\n');
                btns(1) = 1;   %press jump button
            case 'Lateral Grasp'
                fprintf('lateral grasp\n');
                btns(1) = 1;   %press jump button
            case 'Hand Open'
                fprintf('hand open\n');
                btns(1) = 1;   %press jump button
            case 'No Movement'
                fprintf('no movement\n');
                btns = [0 0 0 0]; %reset buttons
                axes = [0 0];  %reset axes
            case 'Wrist Abduction'
                fprintf('wrist abduction\n');
                axes(2) = -32767;   %joystick Y = Up
            case 'Wrist Adduction'
                fprintf('wrist adduction\n');
                axes(2) = 32767;    %joystick Y = Down

        end
    end
    
    %format buttons and axes for sending over UDP
    btn0 = binvec2dec(btns);
    btn0 = typecast(uint64(btn0),'uint8');
    btn0 = btn0(1:ceil(length(btns)/8));
    axis0 = typecast(int16(axes),'uint8');
    
    msg = uint8([length(btns) btn0 length(axes) axis0]);
    a.putData(msg); 
 
end

%a.putData([255 uint8('Q')]) % interrupt code to quit running UDP reciever