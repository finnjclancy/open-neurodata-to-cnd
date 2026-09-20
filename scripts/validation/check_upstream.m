function check_upstream(data_dir, upstream, output_file, feature_index)
if nargin < 4, feature_index=1; end
% Run unmodified upstream mTRF functions on converted, continuous CND data.
% Analysis-only blocking: preserve the stored recording as one trial.
addpath(fullfile(upstream,'CNSP','libs','mTRF-Toolbox_v2','mtrf'));
load(fullfile(data_dir,'dataSub1.mat'),'eeg');
load(fullfile(data_dir,'dataStim.mat'),'stim');
assert(iscell(eeg.data) && iscell(stim.data));
assert(eeg.fs == stim.fs);
if isfield(eeg,'extChan')
    assert(iscell(eeg.extChan), 'CNSP requires extChan to be a cell array');
    assert(size(eeg.extChan{1}.data{1},1) == size(eeg.data{1},1));
end
% Use the full recording at its original clock; no unfiltered decimation.
x=double(stim.data{feature_index,1}); y=double(eeg.data{1});
assert(size(x,1)==size(y,1));
[xtrain,ytrain,xtest,ytest]=mTRFpartition(x,y,5,5);
assert(all(cellfun(@(a) any(a(:)), xtrain)) && any(xtest(:)));
lambdas=[0.1,1,10];
[stats,~]=mTRFcrossval(xtrain,ytrain,eeg.fs,1,0,200,lambdas,'verbose',0);
r=squeeze(mean(mean(stats.r,1),3));
[~,best]=max(r);
model=mTRFtrain(xtrain,ytrain,eeg.fs,1,0,200,lambdas(best),'verbose',0);
[~,teststats]=mTRFpredict(xtest,ytest,model,'verbose',0);
assert(all(isfinite(model.w(:))) && all(isfinite(teststats.r(:))));
result=struct('engine',version,'samples',size(x,1),'channels',size(y,2), ...
 'feature_index',feature_index,'feature_name',stim.names{feature_index}, ...
 'event_samples',nnz(x),'fold_event_counts',[cellfun(@nnz,xtrain);nnz(xtest)],'folds',5,'training_folds',4,'held_out_fold',5, ...
 'lambda',lambdas(best),'mean_test_r',mean(teststats.r(:)), ...
 'finite_weights',all(isfinite(model.w(:))),'unchanged_upstream_functions',true);
fid=fopen(output_file,'w'); fprintf(fid,'%s\n',jsonencode(result)); fclose(fid);
disp(result);
end
