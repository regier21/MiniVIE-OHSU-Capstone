% lspb_minivie.m - Linear Segments with Parabolic Blends
%
% Description: Computes LSPB to compute trajectory given sufficient initial
% conditions.
%
% Params: q0 = initial position
%         qf = final position
%         tf = final time (amount of time to complete trajectory)
%          V = desired constant velocity during middle segment.
%
% Output: qt = trajectory time series with joint angle position data
%
% Also, at the end of the script, qt will be plotted versus time.
%
% NOTE: Appropriate value for V must be given with relation to q0 and qf,
% otherwise, the trajectory will appear discontinuous.
%
% Example values: lspb(0, 40, 20, 3)
%                 lspb(0, 40, 60, 1)
%                 lspb(40, 80, 20, 1)  <-- error case
%
%
% Note the minimum time to complete an lspb move is:
%   (qf - q0) / V)
%
%
% Revisions:
%   2016Sept21 Armiger: Created

function qt = lspb_minivie(q0, qf, tf, V)

% check scaling since segment equations assume qf > q0, so just flip as
% needed
if qf < q0
    scale = -1;
    q0 = -q0;
    qf = -qf;
else
    scale = 1;
end

% assume t0 = 0 and tf > 0
dt = 0.02;
% define implicit time
t = 0:dt:tf;

% check if start and end angles are the same
if abs(q0 - qf) < 0.01
    qt = qf*ones(size(t));
    t_1 = 0;
    t_3 = tf;
    qt_1 = qf;
    qt_3 = qf;
    
else
    % check that velocity is sufficient for motion
    assert( ((qf - q0) / V) < tf, ' insufficient time')
    
    % We will allow the user to go slower than velocity provided
    %assert( (2*(qf - q0) / V) >= tf, ' max velocity reached')
    if (2*(qf - q0) / V) <= tf
        V = 2*(qf - q0) / tf;
        V = max(V,1e-6);  % ensure V is never zero
    end
    
    % qt is the time history trajectory for the motion
    % qf is the final destination value
    % alpha is
    % tf is the final time in seconds
    
    tb = (q0 - qf + V*tf) / V;
    alpha = V / tb;
    
    % label the time history into segments:
    tLabel = 3*ones(size(t));
    tLabel(t <= tb) = 1;
    tLabel( (tb < t) & (t <= (tf-tb) ) ) = 2;
    tLabel( (tf-tb) < t ) = 3;
    
    t_1 = t( tLabel == 1 );
    t_2 = t( tLabel == 2 );
    t_3 = t( tLabel == 3);
    
    qt_1 = q0 + (0.5*alpha*t_1.^2);
    qt_2 = 0.5*(qf + q0 - V*tf) + V*t_2;
    qt_3 = qf - 0.5*alpha*tf^2 + alpha*tf*t_3 - (alpha/2)*t_3.^2;
    
    qt_1 = scale*qt_1;
    qt_2 = scale*qt_2;
    qt_3 = scale*qt_3;
    
    qt = cat(2,qt_1,qt_2,qt_3);
    
end

if length(t) ~= length(qt)
    error('error creating trajectory')
end

% Plot trajectory
if nargout < 1
    plot(t, qt,'Marker','.');
    line(t_1(end), qt_1(end),'Color','r','Marker','o')
    line(t_3(1), qt_3(1),'Color','r','Marker','o')
    xlabel('Time (sec)');
    ylabel('Angle (deg)');
    set(gcf, 'Name', 'LPSB Plot');
end

return

%% Test Area: Use Cell Function Mode to execute and test values
q0 = 0;
qf = -40;
V = 50;
tf = 1;
lspb_minivie(q0,qf,V,tf);
