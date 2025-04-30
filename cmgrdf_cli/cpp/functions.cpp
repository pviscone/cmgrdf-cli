#ifndef __FUNCTIONS_CPP__
#define __FUNCTIONS_CPP__

using namespace ROOT;

auto generator = TRandom();

//_____________________________________________________________________________

float if3(bool cond, float iftrue, float iffalse) {
    return cond ? iftrue : iffalse;
}

#endif