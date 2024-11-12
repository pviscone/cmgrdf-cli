#pragma once
#include "ROOT/RVec.hxx"
#include "Math/Vector4Dfwd.h"

using namespace ROOT::VecOps;
using namespace ROOT::Math;
using namespace ROOT;

auto generator = TRandom();

//_____________________________________________________________________________

float if3(bool cond, float iftrue, float iffalse) {
    return cond ? iftrue : iffalse;
}
