function check_matlab_cnsp(data_dir, upstream, output_file, feature_index)
if nargin < 4, feature_index=1; end
% Run the CNSP 2025 1-8 Hz preprocessing sequence and a held-out forward TRF.
% Requires MATLAB and its filter-design/Signal Processing functionality.
% Uses unchanged upstream functions. Dataset configuration: average reference,
% selected feature, one continuous run partitioned into five analysis folds.
% This is a configured integration driver, not the unchanged tutorial script.
if exist('OCTAVE_VERSION','builtin')
    error('CND:MatlabRequired','This check requires MATLAB, not Octave.');
end
if exist('fdesign.lowpass','file') == 0 && exist('fdesign.lowpass','class') == 0
    error('CND:FilterDesignRequired','MATLAB fdesign.lowpass is required.');
end
addpath(genpath(fullfile(upstream,'CNSP','libs','cnsp_utils')));
addpath(genpath(fullfile(upstream,'CNSP','libs','eeglab','functions')));
addpath(fullfile(upstream,'CNSP','libs','mTRF-Toolbox_v2','mtrf'));
neural_files=dir(fullfile(data_dir,'dataSub*.mat'));
assert(numel(neural_files)==1,'Expected exactly one dataSub*.mat file');
load(fullfile(data_dir,neural_files(1).name),'eeg');
load(fullfile(data_dir,'dataStim.mat'),'stim');
assert(iscell(eeg.data) && numel(eeg.data)==1,'Expected one continuous run');
original_fs=eeg.fs;
assert(iscell(eeg.extChan),'External groups must be MATLAB cells');
% Same order and functions as CNSP2025_EEGpreprocessing.m, band 5.
lf=getLPFilt(eeg.fs,8);
eeg.data=cellfun(@(x) filtfilthd(lf,x),eeg.data,'UniformOutput',false);
for g=1:numel(eeg.extChan)
    eeg.extChan{g}.data=cellfun(@(x) filtfilthd(lf,x),eeg.extChan{g}.data,'UniformOutput',false);
end
eeg=cndDownsample(eeg,64);
hf=getHPFilt(eeg.fs,1);
eeg.data=cellfun(@(x) filtfilthd(hf,x),eeg.data,'UniformOutput',false);
for g=1:numel(eeg.extChan)
    eeg.extChan{g}.data=cellfun(@(x) filtfilthd(hf,x),eeg.extChan{g}.data,'UniformOutput',false);
end
for tr=1:numel(eeg.data)
    eeg.data{tr}=removeBadChannels(eeg.data{tr},eeg.chanlocs,[],3,3);
end
% ERP CORE EOG channels are not mastoid references.
eeg=cndReref(eeg,'Avg');
if stim.fs ~= 64
    stim=cndDownsample(stim,64);
end
assert(eeg.fs==64 && stim.fs==64,'Analysis clocks did not reconcile');
x=[];
if feature_index == 0
    for feature=1:size(stim.data,1)
        x=[x double(stim.data{feature,1})]; %#ok<AGROW>
    end
else
    x=double(stim.data{feature_index,1});
end
y=double(eeg.data{1});
n=min(size(x,1),size(y,1));
assert(abs(size(x,1)-size(y,1))<=1,'Unexpected duration difference');
x=x(1:n,:);y=y(1:n,:);
% Exclude idle data after the task, while retaining the longest positive lag.
last_event=find(any(x~=0,2),1,'last');
assert(~isempty(last_event),'Selected predictor contains no events');
n=min(n,last_event+ceil(0.6*64));
x=x(1:n,:);y=y(1:n,:);
[xtrain,ytrain,xtest,ytest]=mTRFpartition(x,y,5,5);
assert(all(cellfun(@(a) any(a(:)),xtrain)) && any(xtest(:)));
lambdas=[.1,1,10];
% Use the same regularizer for parameter selection and the final multivariate fit.
regularization_method='ridge';
stats=mTRFcrossval(xtrain,ytrain,64,1,-100,600,lambdas,'method',regularization_method,'verbose',0);
r=squeeze(mean(mean(stats.r,1),3));
assert(all(isfinite(r(:))));
[~,best]=max(r);
model=mTRFtrain(xtrain,ytrain,64,1,-100,600,lambdas(best),'method',regularization_method,'verbose',0);
[~,teststats]=mTRFpredict(xtest,ytest,model,'verbose',0);
assert(all(isfinite(model.w(:))) && all(isfinite(teststats.r(:))));
result=struct('engine',version,'upstream_preprocessing',true,'original_fs',original_fs, ...
    'analysis_fs',64,'samples',n,'channels',size(y,2),'folds',5, ...
    'reference','Avg','feature_index',feature_index,'predictor_columns',size(x,2), ...
    'regularization_method',regularization_method, ...
    'training_folds',4,'held_out_fold',5, ...
    'active_task_trim',true,'lambda',lambdas(best), ...
    'mean_test_r',mean(teststats.r(:)),'finite_weights',true);
fid=fopen(output_file,'w');assert(fid>=0); cleaner=onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));
end
