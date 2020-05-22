tdPath = 'C:\GIT\bitbucket_minivie_dev\+Inputs\@EmgSimulator\private\DEFAULT.trainingData';
savePath = 'C:\GIT\bitbucket_minivie_dev\+Inputs\@EmgSimulator\private\emgPatternData2';

td = PatternRecognition.TrainingData(tdPath);

numClasses = td.NumClasses;
emgPatternData = cell(1,numClasses);
dataBreaks = cell(1,numClasses);

for i = 1:numClasses
    [emgPatternData{i}, dataBreaks{i}] = td.getClassData(i,1);
end

save(savePath, 'emgPatternData','classNames');

figure()
plot(td.getContinuousData(1));
