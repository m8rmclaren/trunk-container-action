## Continuous Integration

- **Push to `main`**
	1. Calculate the next RC tag _from GHCR tags_:
		- **No tags yet** -> next tag `1.0.0-rc.0`
		- **Most recent tag is `x.y.z`** -> next tag `x.[y+1].0-rc.0`
		- **Most recent tag is `x.y.z-rc.n`** -> next tag `x.y.z-rc.[n+1]`
	2. Build image with calculated next tag
- **Push to `release-x.y`**
	1. Calculate the next tag _from GHCR tags_:
		- **No tags yet matching `x.y.0`** -> next tag `x.y.0`
		- **There exists `x.y.[0<=n<=inf]`** -> next tag `x.y.[n+1]`
	2. Determine where the image comes from:
		- **Next tag is `x.y.0`** -> Re-tag `x.y.0-rc.n` as `x.y.0` where `n` is the latest RC
		- **Next tag is `x.y.[0<=n<=inf]`** -> Build image off of `release-x.y`
	3. Create GitHub release
