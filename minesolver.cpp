#include "minesolver.h"
#include <vector>
#include <random>
#include <atomic>
#include <algorithm>

static int G_R=0, G_C=0, G_B=0, G_SAMPLES=10000;
static std::vector<int> revealed; 
// -1=unknown, 0..4=hints, 5=bomb

inline int idx(int r,int c){ return r*G_C + c; }
static const int DR[8]={-1,-1,-1,0,0,1,1,1}, DC[8]={-1,0,1,-1,1,-1,0,1};

void ms_init(int rows,int cols,int bombs,int sample_count){
    G_R=rows; G_C=cols; G_B=bombs; G_SAMPLES=sample_count;
    revealed.assign(rows*cols, -1);
}

void ms_set_sample_count(int sample_count){
    G_SAMPLES = sample_count;
}

void ms_set_cell(int r,int c,int value){
    revealed[idx(r,c)] = value;
}

void ms_cleanup(){
    revealed.clear();
    G_R=G_C=G_B=0;
}

// Check a placement against hints & revealed bombs
bool check_placement(const std::vector<char>& hasBomb){
    int N = G_R * G_C;
    for(int i=0;i<N;++i){
        int v = revealed[i];
        if(v==5){
            if(!hasBomb[i]) return false;
        }
        else if(v>=0 && v<=4){
            int r=i/G_C, c=i%G_C, cnt=0;
            for(int k=0;k<8;++k){
                int nr=r+DR[k], nc=c+DC[k];
                if(nr>=0&&nr<G_R&&nc>=0&&nc<G_C)
                    cnt+=hasBomb[idx(nr,nc)];
            }
            bool ok=false;
            switch(v){
              case 0: ok=(cnt==0); break;
              case 1: ok=(cnt>=1&&cnt<=2); break;
              case 2: ok=(cnt>=3&&cnt<=4); break;
              case 3: ok=(cnt>=5&&cnt<=6); break;
              case 4: ok=(cnt>=7&&cnt<=8); break;
            }
            if(!ok) return false;
        }
    }
    return true;
}

// Monte Carlo solver
void ms_solve(float* out_probs){
    int N = G_R * G_C;
    // prepare fixed/unknown lists
    std::vector<int> fixed_idxs, unk_idxs;
    for(int i=0;i<N;++i){
        if(revealed[i]==5)        fixed_idxs.push_back(i);
        else if(revealed[i]==-1)  unk_idxs.push_back(i);
    }
    int bombs_remain = G_B - int(fixed_idxs.size());
    if(bombs_remain<0) bombs_remain=0;

    std::vector<std::atomic<int>> hit(N);
    for(int i=0;i<N;++i) hit[i]=0;
    std::vector<char> placement(N);
    std::mt19937_64 rng(std::random_device{}());

    int valid=0;
    for(int iter=0;iter<G_SAMPLES;++iter){
        std::fill(placement.begin(), placement.end(), 0);
        for(int i: fixed_idxs) placement[i]=1;
        std::shuffle(unk_idxs.begin(), unk_idxs.end(), rng);
        for(int k=0;k<bombs_remain && k<int(unk_idxs.size());++k)
            placement[unk_idxs[k]] = 1;
        if(!check_placement(placement)) continue;
        ++valid;
        for(int i=0;i<N;++i)
            if(placement[i]) hit[i].fetch_add(1, std::memory_order_relaxed);
    }
    for(int i=0;i<N;++i){
        out_probs[i] = valid>0 ? float(hit[i].load())/float(valid) : 0.0f;
    }
}

// Exact solver via combination‐enumeration
void ms_solve_exact(float* out_probs){
    int N = G_R * G_C;
    std::vector<int> fixed_idxs, unk_idxs;
    for(int i=0;i<N;++i){
        if(revealed[i]==5)        fixed_idxs.push_back(i);
        else if(revealed[i]==-1)  unk_idxs.push_back(i);
    }
    int bombs_remain = G_B - int(fixed_idxs.size());
    if(bombs_remain<0) bombs_remain=0;
    int U = int(unk_idxs.size());

    std::vector<long long> hit(N,0);
    long long valid=0;
    std::vector<char> placement(N);

    // generate all combinations of size bombs_remain from unk_idxs
    std::vector<int> comb(bombs_remain);
    for(int i=0;i<bombs_remain;++i) comb[i]=i;
    bool done = (bombs_remain==0);
    while(!done){
        // build placement
        std::fill(placement.begin(), placement.end(), 0);
        for(int i: fixed_idxs) placement[i]=1;
        for(int k=0;k<bombs_remain;++k)
            placement[ unk_idxs[ comb[k] ] ] = 1;

        if(check_placement(placement)){
            ++valid;
            for(int i=0;i<N;++i)
                if(placement[i]) hit[i]++;
        }
        // next combination
        int i=bombs_remain-1;
        while(i>=0 && comb[i]==U-bombs_remain+i) --i;
        if(i<0) done=true;
        else{
            ++comb[i];
            for(int j=i+1;j<bombs_remain;++j)
                comb[j]=comb[j-1]+1;
        }
    }
    for(int i=0;i<N;++i){
        out_probs[i] = valid>0 ? float(hit[i])/float(valid) : 0.0f;
    }
}
